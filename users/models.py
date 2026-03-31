from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)
from django.utils import timezone
from django.conf import settings
import uuid

from documents.services.export.report_type import ReportType
from knowledge_base.models import AccountingRegime


"""Tạo user thường"""
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("User phải có email")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # mã hóa mật khẩu
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Tạo superuser"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email, password, **extra_fields)

"""Model User tùy biến cho hệ thống"""
class User(AbstractBaseUser, PermissionsMixin):
    avatar = models.ImageField(upload_to='upload/%Y/%m', blank=True, null=True, verbose_name=("Ảnh đại diện"))
    email = models.EmailField(unique=True, max_length=255)
    full_name = models.CharField(max_length=255, blank=True, null=True, verbose_name=("Họ tên"))
    phone = models.CharField(max_length=15, blank=True, null=True, verbose_name=("Số điện thoại"))
    broker_code = models.CharField(max_length=100, blank=True, null=True,
                                   verbose_name=("Mã người giới thiệu"))  # mã người môi giới

    # ================================
    # STATUS
    # ================================
    is_active = models.BooleanField(default=True, verbose_name=("Kích hoạt"))
    is_staff = models.BooleanField(default=False, verbose_name=("Quản trị viên"))

    # ================================
    # ONBOARDING (🔥 QUAN TRỌNG)
    # ================================
    is_onboarded = models.BooleanField(default=False, db_index=True)
    onboarded_at = models.DateTimeField(null=True, blank=True)

    # Trạng thái & quyền
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name=("Ngày tạo"))
    last_login = models.DateTimeField(null=True, blank=True, verbose_name=("Đăng nhập gần nhất"))

    objects = UserManager()

    USERNAME_FIELD = "email"  # login bằng email
    REQUIRED_FIELDS = []  # các trường bắt buộc khác khi tạo superuser

    def __str__(self):
        return self.email

""" Tạo Tenant """
class Organization(models.Model):

    # =============================
    # LEGAL FORM
    # =============================
    class LegalForm(models.TextChoices):
        HKD = "HKD", "Hộ kinh doanh"
        ENTERPRISE = "ENTERPRISE", "Doanh nghiệp"

    # =============================
    # STATUS (SYSTEM LEVEL)
    # =============================
    class Status(models.TextChoices):
        PENDING = "pending", "Chờ kích hoạt"
        ACTIVE = "active", "Đang hoạt động"
        SUSPENDED = "suspended", "Tạm khóa"

    # =============================
    # BASIC INFO
    # =============================
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, null=True, blank=True)

    tax_code = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True
    )

    legal_form = models.CharField(
        max_length=20,
        choices=LegalForm.choices,
    )

    # =============================
    # STATUS CONTROL
    # =============================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    is_active = models.BooleanField(default=True)

    # =============================
    # LIFECYCLE
    # =============================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    activated_at = models.DateTimeField(null=True, blank=True)

    # =============================
    # RELATIONS
    # =============================
    industries = models.ManyToManyField(
        'Industry',
        through="OrganizationIndustry",
        related_name="organizations",
    )

    # =============================
    # BUSINESS LOGIC
    # =============================

    def is_pending(self):
        return self.status == self.Status.PENDING

    def is_active_org(self):
        return self.status == self.Status.ACTIVE and self.is_active

    def mark_active(self):
        self.status = self.Status.ACTIVE
        self.activated_at = timezone.now()
        self.save(update_fields=["status", "activated_at"])

    def mark_suspended(self):
        self.status = self.Status.SUSPENDED
        self.save(update_fields=["status"])

    # 🔥 CORE CHECK (QUAN TRỌNG NHẤT)
    def is_usable(self):
        """
        Org usable khi:
        - active
        - có subscription
        - subscription còn hạn
        """
        if not self.is_active:
            return False

        if self.status != self.Status.ACTIVE:
            return False

        if not hasattr(self, "subscription"):
            return False

        return self.subscription.is_active()

    # =============================
    # STRING
    # =============================
    def __str__(self):
        return f"{self.name} ({self.status})"

class OrganizationMember(models.Model):
    class Meta:
        unique_together = ("user", "organization")

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="memberships"   # ✅ thêm dòng này
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="members"       # ✅ thêm dòng này
    )

    ROLE_CHOICES = (
        ("OWNER", "Chủ sở hữu"),
        ("ADMIN", "Quản trị"),
        ("ACCOUNTANT", "Kế toán"),
        ("VIEWER", "Xem"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Subscription(models.Model):

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["current_period_end"]),
        ]

    # =============================
    # STATUS
    # =============================
    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    # =============================
    # RELATION
    # =============================
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscription"
    )

    plan = models.ForeignKey("Plan", on_delete=models.PROTECT)

    # =============================
    # BILLING PERIOD
    # =============================
    current_period_start = models.DateField()
    current_period_end = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )

    # =============================
    # BUSINESS LOGIC
    # =============================

    def is_active(self):
        """
        Subscription còn hiệu lực
        """
        if self.status != self.STATUS_ACTIVE:
            return False

        if self.current_period_end < timezone.now().date():
            return False

        return True

    def mark_expired(self):
        self.status = self.STATUS_EXPIRED
        self.save(update_fields=["status"])

    def cancel(self):
        self.status = self.STATUS_CANCELLED
        self.save(update_fields=["status"])

    # =============================
    # STRING
    # =============================
    def __str__(self):
        return f"{self.organization.name} - {self.status}"

class Plan(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    max_users = models.IntegerField(default=1)
    max_documents_per_month = models.IntegerField(default=100)

    is_active = models.BooleanField(default=True)
    is_highlighted = models.BooleanField(default=False)  # gói đề xuất

    sort_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["sort_order"]),
        ]

class PlanModule(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    module = models.ForeignKey('Module', on_delete=models.CASCADE)

    class Meta:
        unique_together = ("plan", "module")

""" Module (Chức năng SaaS), lưu và quản lý 'Hộ kinh doanh', 'Doanh nghiệp', 'Quản lý nhân sự',... """
class Module(models.Model):
    code = models.CharField(max_length=50, unique=True) # ACCOUNTING, HRM
    name = models.CharField(max_length=255)             # Hộ kinh doanh, Kế toán doanh nghiệp
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)   # admin bật/tắt module toàn hệ thống

    # 🔥 thêm field này sau để quản lý Module cho Public đăng ký lần đầu
    is_public_enabled = models.BooleanField(default=True)

    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

""" Quản lý module được bật / tắt cho từng Organization (Tenant)/ Gán module cho org """
class OrganizationModule(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="organization_modules")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="organization_modules")
    is_enabled = models.BooleanField(default=True)
    activated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "module")

    def __str__(self):
        return f"{self.organization.name} - {self.module.code}"

""" AccountingProfile ⭐ (Hồ sơ kế toán – TRUNG TÂM)/Hồ sơ kế toán theo org + module """
class AccountingProfile(models.Model):
    name = models.CharField(max_length=255)
    tax_code = models.CharField(max_length=50)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="accounting_profiles"
    )

    accounting_regime = models.ForeignKey(
        AccountingRegime,
        on_delete=models.PROTECT
    )

    fiscal_year_start = models.DateField()

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.tax_code})"

class ProfileUser(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Chủ sở hữu"
        ACCOUNTANT = "ACCOUNTANT", "Kế toán"
        STAFF = "STAFF", "Nhân viên"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile = models.ForeignKey(AccountingProfile, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices)

    class Meta:
        unique_together = ("user", "profile")

""" Danh sách quyền của từng module/ """
class ModulePermission(models.Model):
    """
    Ví dụ:
        ACCOUNTING_DN:view
        ACCOUNTING_DN:approve
        INVENTORY:import
    """
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="permissions"
    )

    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ("module", "code")

    def __str__(self):
        return f"{self.module.code}:{self.code}"

""" Gán quyền module cho từng thành viên """
class MemberModulePermission(models.Model):
    member = models.ForeignKey(OrganizationMember, on_delete=models.CASCADE, related_name="module_permissions")
    permission = models.ForeignKey('ModulePermission', on_delete=models.CASCADE)
    is_allowed = models.BooleanField(default=True)

    class Meta:
        unique_together = ("member", "permission")

""" ProfileModule (Bật/tắt chức năng) """
class ProfileModule(models.Model):
    profile = models.ForeignKey(AccountingProfile, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=True)


    class Meta:
        unique_together = ('profile', 'module')

""" ProfileDrive (Google Drive theo hồ sơ kế toán) """
class ProfileDrive(models.Model):
    profile = models.OneToOneField(
    AccountingProfile,
    on_delete=models.CASCADE,
    related_name='drive'
    )
    root_folder_id = models.CharField(max_length=255)

    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    token_expiry = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

"""Quản lý thư mục gốc Drive cho User"""
class UserDrive(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="drive"
    )
    drive_folder_id = models.CharField(
        max_length=255,
        help_text="ID thư mục Google Drive chính của User"
    )

    access_token = models.TextField(
        help_text="Access token để kết nối Google Drive",
        null=True,
        blank=True
    )
    refresh_token = models.TextField(
        help_text="Refresh token để làm mới access token",
        null=True,
        blank=True
    )
    token_expiry = models.DateTimeField(
        help_text="Thời điểm hết hạn của access token",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Google Drive của {self.user.email} - FolderID: {self.drive_folder_id}"

"""Quản lý thư mục con trong Drive và File Sheet"""
class DriveFolder(models.Model):
    NODE_TYPE_CHOICES = (
        ("folder", "Folder"),
        ("sheet", "Google Sheet"),
        ("upload", "Upload Folder"),
    )

    drive = models.ForeignKey(
        UserDrive,
        on_delete=models.CASCADE,
        related_name="nodes"
    )

    name = models.CharField(
        max_length=255,
        help_text="Tên thư mục hoặc Google Sheet"
    )

    # 🔹 Chỉ dùng cho folder
    folder_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="Google Drive Folder ID"
    )

    # 🔹 Chỉ dùng cho Google Sheet
    sheet_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="Google Sheet File ID"
    )

    node_type = models.CharField(
        max_length=20,
        choices=NODE_TYPE_CHOICES,
        default="folder"
    )

    parent_folder = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["drive"]),
            models.Index(fields=["node_type"]),
        ]

    def __str__(self):
        return f"{self.name}"

"""quản lý thiết bị đăng nhập/ Đánh dấu onboard xong"""
class UserSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions"
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions"
    )

    active_module = models.ForeignKey(
        Module,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions"
    )

    device_name = models.CharField(max_length=255, blank=True, null=True)
    user_agent = models.CharField(max_length=512, blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    session_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    created_at = models.DateTimeField(default=timezone.now)
    last_active = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)

class SubscriptionPeriod(models.Model):
    MONTH_OPTIONS = (
        (1, "1 Month"),
        (12, "12 Months"),
        (24, "24 Months"),
        (36, "36 Months"),
    )

    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name="periods"
    )

    months = models.IntegerField(choices=MONTH_OPTIONS)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("plan", "months")
        ordering = ["months"]

    def __str__(self):
        return f"{self.plan.code} - {self.months} months"

class Payment(models.Model):

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    period = models.ForeignKey(
        SubscriptionPeriod,
        on_delete=models.PROTECT
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="VND")

    transaction_id = models.CharField(max_length=255, null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.amount} - {self.status}"

class Industry(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)

    vat_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    pit_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "industries"
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"

class OrganizationIndustry(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="organization_industries",
    )

    industry = models.ForeignKey(
        Industry,
        on_delete=models.CASCADE,
        related_name="organization_industries",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "organization_industries"
        unique_together = ("organization", "industry")

    def __str__(self):
        return f"{self.organization.name} - {self.industry.name}"

# Chưa Makemigrations
class PaymentTransaction(models.Model):
    pass
    # order_id = models.CharField(...)
    # user = models.ForeignKey(User)
    # plan = models.ForeignKey(Plan)
    # amount = models.IntegerField()
    # status = models.CharField(...)