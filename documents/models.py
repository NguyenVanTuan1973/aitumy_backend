from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from unidecode import unidecode

from pdf2image import convert_from_path
from django.core.files.base import ContentFile
from io import BytesIO
import os

from users.models import UserDrive, DriveFolder

User = settings.AUTH_USER_MODEL

DOC_ROLE_CHOICES = [
    ("main", "Chứng từ hạch toán"),
    ("support", "Chứng từ bổ trợ"),
]

STATUS_CHOICES = [
    ("enable", "Enable"),
    ("disabled", "Disabled"),
    ("invalid", "Invalid"),
    ("pending", "Pending"),
]

class DocumentMetadata(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")  # User ID

    # Thông tin file gốc
    original_filename = models.CharField(max_length=255)        # Tên file gốc chứng từ
    file_name = models.CharField(max_length=255)                # tên chuẩn hóa
    file_format = models.CharField(max_length=20)               # Định dạng file
    file_size = models.BigIntegerField(null=True, blank=True)   # Kích cỡ file

    # Thông tin phân tích/extract
    doc_type = models.CharField(max_length=100, null=True, blank=True)  # Phân loại CT theo nhóm phân hệ KT
    doc_no = models.CharField(max_length=100, null=True, blank=True)    # Số chứng từ
    doc_date = models.DateField(null=True, blank=True)                  # Ngày chứng từ
    tax_code = models.CharField(max_length=50, null=True, blank=True)   # MST đối tượng
    description = models.TextField(null=True, blank=True)               # Nội dung tóm tắt chứng từ
    payment_method = models.CharField(max_length=50, null=True, blank=True) # Hình thức thanh toán
    tax_rate = models.FloatField(null=True, blank=True)                     # % Thuế
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)    # Tiền thuế
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)  # Tiền hàng hóa, DV
    discount_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)   # Tiền chiêt khấu
    payment_date = models.DateField(null=True, blank=True)      # Ngày hẹn thanh toán

    # Tình trạng kế toán
    accounting_status = models.CharField(max_length=50, default="Chưa ghi sổ")  # Tình trạng CT đã ghi sổ hay chưa ?
    bookkeeping_date = models.DateField(null=True, blank=True)                  # Ngày ghi sổ
    accounting_code = models.CharField(max_length=128, null=True, blank=True)   # Mã hạch toán N10C20

    # 🔗 Liên kết Google Drive
    drive_file_id = models.CharField(max_length=255, null=True, blank=True)     # file ID của Google Drive
    drive_path = models.CharField(max_length=1024, null=True, blank=True)       # Đường dẫn lưu file
    drive_mime = models.CharField(max_length=100, null=True, blank=True)
    drive_link = models.URLField(null=True, blank=True)

    upload_date = models.DateTimeField(auto_now_add=True)       # Ngày upload file
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")     # Tình trạng

    # raw OCR text / extract logs
    ocr_text = models.TextField(null=True, blank=True)      # Dữ liệu Extract từ file
    extract_log = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.file_name} ({self.user})"

class DocumentGroup(models.Model):
    # bộ chứng từ (ví dụ: Mua hàng HD1234)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="document_groups")
    group_code = models.CharField(max_length=100, null=True, blank=True, unique=True)
    group_name = models.CharField(max_length=255)
    group_type = models.CharField(max_length=100, null=True, blank=True) # MuaHang/BanHang/...
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.group_name} - {self.user}"

class GroupDocument(models.Model):
    # liên kết n-n với vai trò main/support
    group = models.ForeignKey(DocumentGroup, on_delete=models.CASCADE, related_name="group_documents")
    document = models.ForeignKey(DocumentMetadata, on_delete=models.CASCADE, related_name="document_groups")
    role = models.CharField(max_length=20, choices=DOC_ROLE_CHOICES, default="support")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "document")

    def __str__(self):
        return f"{self.document.file_name} in {self.group.group_name} ({self.role})"

class FormTemplate(models.Model):
    # ====== 1️⃣ Thông tin cơ bản ======
    code = models.CharField(
        max_length=50, unique=True,
        help_text="Mã biểu mẫu theo quy định (VD: 01-TT, 02-VT, 01a-LĐTL...)"
    )
    name = models.CharField(
        max_length=255,
        help_text="Tên đầy đủ của biểu mẫu (VD: Phiếu thu, Phiếu chi, Hóa đơn GTGT...)"
    )
    title = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Tiêu đề ngắn dùng để match mạnh (VD: 'PHIẾU THU')"
    )

    description = models.TextField(
        blank=True, null=True,
        help_text="Mô tả chi tiết nội dung, mục đích sử dụng biểu mẫu."
    )
    regulation_source = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Nguồn quy định hoặc thông tư gốc (VD: 152/2025/TT-BTC, 99/2025/TT-BTC...)"
    )
    version = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="Phiên bản hoặc năm ban hành biểu mẫu."
    )
    category = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Nhóm biểu mẫu (VD: Kế toán, Thuế, Lao động, Ngân hàng, ...)"
    )

    # ====== 2️⃣ File mẫu lưu cục bộ (local) ======
    pdf_file = models.FileField(
        upload_to='documents/pdf/', blank=True, null=True,          # media/documents/pdf/
        help_text="File PDF của biểu mẫu gốc (chuẩn theo thông tư)."
    )
    docx_file = models.FileField(
        upload_to='documents/docx/', blank=True, null=True,         # media/documents/pdf/
        help_text="File DOCX của biểu mẫu (dùng để sinh chứng từ tự động)."
    )
    image_preview = models.ImageField(
        upload_to='documents/image/', blank=True, null=True,        # media/documents/image/templates/image
        help_text="Ảnh xem trước hoặc thumbnail của biểu mẫu."
    )

    # ====== 3️⃣ Cấu trúc nhận diện / trích xuất ======
    structure_json = models.JSONField(
        blank=True, null=True,
        help_text=(
            "Cấu trúc dữ liệu ánh xạ các trường trên biểu mẫu, "
            "gồm vị trí, tên trường, regex nhận dạng, label, v.v."
        )
    )

    example_text = models.TextField(
        blank=True, null=True,
        help_text="Ví dụ text OCR của biểu mẫu (dùng để train)."
    )

    keywords = models.TextField(
        blank=True, null=True,
        help_text="Từ khóa (có dấu), cách nhau bởi dấu phẩy."
    )

    # ====== ⚙️ 4️⃣ TRƯỜNG CHUẨN HÓA (Normalized) ======
    code_norm = models.CharField(max_length=80, blank=True, null=True, db_index=True)
    title_norm = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    keywords_norm = models.TextField(blank=True, null=True)  # Lưu dạng: "phieu thu,ma so,so tien"

    # ====== 4️⃣ Định nghĩa nhóm lưu chứng từ trên Drive ======
    drive_group_path = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=(
            "Tên nhóm folder lưu chứng từ trên Drive của mỗi user, "
            "VD: 'chung_tu_ke_toan/tien_mat' hoặc 'hoa_don/ban_ra'"
        )
    )

    # ====== 5️⃣ Quản trị & AI sử dụng ======
    is_active = models.BooleanField(default=True, help_text="Trạng thái hoạt động của mẫu.")
    confidence_threshold = models.FloatField(
        default=0.3,
        help_text="Ngưỡng xác suất (0–1) để AI nhận diện mẫu này là khớp."
    )
    created_by = models.ForeignKey(
        UserDrive, on_delete=models.SET_NULL,
        blank=True, null=True, help_text="Người tạo hoặc quản lý mẫu này."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # -------------------------------------------------------------------------------------
    # 🔥 7️⃣ Validate cấu trúc JSON (structure_json)
    # -------------------------------------------------------------------------------------
    def clean(self):
        if self.structure_json and not isinstance(self.structure_json, dict):
            raise ValidationError("structure_json phải là JSON object hợp lệ.")
        if self.structure_json and "fields" not in self.structure_json:
            raise ValidationError("structure_json phải có key 'fields'.")

    # -------------------------------------------------------------------------------------
    # 🔥 8️⃣ Hàm tiện ích cho AI detect
    # -------------------------------------------------------------------------------------
    def get_keywords(self):
        if not self.keywords_norm:
            return []
        return [k.strip() for k in self.keywords_norm.split(",") if k.strip()]

    def get_fields(self):
        if self.structure_json and "fields" in self.structure_json:
            return self.structure_json["fields"]
        return {}

    # -------------------------------------------------------------------------------------
    # 🔥 9️⃣ Normalize tất cả dữ liệu để AI matching chính xác
    # -------------------------------------------------------------------------------------
    def save(self, *args, **kwargs):
        # -------- Normalize mã biểu mẫu --------
        if self.code:
            c = self.code.lower().strip()
            c = c.replace(" ", "").replace("–", "-").replace("—", "-")
            self.code_norm = c

        # -------- Normalize title (ưu tiên title, fallback name) --------
        title_src = self.title if self.title else self.name
        if title_src:
            try:
                self.title_norm = unidecode(title_src.lower()).strip()
            except Exception:
                self.title_norm = title_src.lower().strip()

        # -------- Normalize keywords (xóa dấu – bỏ từ < 3 ký tự) --------
        kws = []
        if self.keywords:
            for kw in str(self.keywords).replace("\n", ",").split(","):
                k = kw.strip()
                if not k:
                    continue
                try:
                    k_norm = unidecode(k.lower()).strip()
                except Exception:
                    k_norm = k.lower().strip()
                if len(k_norm) < 3:  # bỏ từ quá ngắn
                    continue
                kws.append(k_norm)
        self.keywords_norm = ",".join(dict.fromkeys(kws))  # loại duplicate

        # ---------------------------------------------------------------------------------
        # 🔥 10️⃣ tạo thumbnail PDF nếu chưa có
        # ---------------------------------------------------------------------------------
        super().save(*args, **kwargs)

        if self.pdf_file and not self.image_preview:
            try:
                pdf_path = self.pdf_file.path
                pages = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=1)
                if pages:
                    img = pages[0]
                    img_io = BytesIO()
                    img.save(img_io, format="JPEG", quality=85)

                    base = os.path.splitext(os.path.basename(pdf_path))[0]
                    thumb_name = f"{base}_preview.jpg"

                    self.image_preview.save(
                        f"documents/image/{thumb_name}",
                        ContentFile(img_io.getvalue()),
                        save=False
                    )
                    super().save(update_fields=['image_preview'])

            except Exception as e:
                print("❌ Lỗi tạo thumbnail PDF:", e)

    # -------------------------------------------------------------------------------------
    # 🔥 11️⃣ Hiển thị
    # -------------------------------------------------------------------------------------
    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        ordering = ["code"]
        verbose_name = "Biểu mẫu kế toán"
        verbose_name_plural = "Danh mục Biểu mẫu (Form Templates)"

class RegisterMapping(models.Model):
    """
    Mapping plan + flow -> form template
    """

    PLAN_CHOICES = [
        ("hkd", "HKD"),
        ("hkd_plus", "HKD Plus"),
        ("hkd_pro", "HKD Pro"),
    ]

    FLOW_CHOICES = [
        ("income", "Income"),
        ("expense", "Expense"),
    ]

    plan_code = models.CharField(max_length=50, choices=PLAN_CHOICES)

    flow = models.CharField(
        max_length=20,
        choices=FLOW_CHOICES
    )

    form_template = models.ForeignKey(
        FormTemplate,
        on_delete=models.CASCADE
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("plan_code", "flow")

    def __str__(self):
        return f"{self.plan_code} - {self.flow}"

class AccountingBook(models.Model):

    code = models.CharField(max_length=20)

    name = models.CharField(max_length=255)

    plan = models.CharField(
        max_length=20,
        choices=[
            ("hkd", "Hộ kinh doanh"),
            ("hkd_plus", "HKD Plus"),
            ("hkd_pro", "HKD Pro"),
            ("enterprise", "Doanh nghiệp"),
        ]
    )

    regulation = models.CharField(
        max_length=100,
        help_text="Thông tư áp dụng"
    )

    # loại sổ
    book_type = models.CharField(
        max_length=20,
        choices=[
            ("general", "Sổ tổng hợp"),
            ("detail", "Sổ chi tiết"),
            ("journal", "Nhật ký"),
            ("report", "Báo cáo"),
        ]
    )

    # cấu trúc cây
    parent_book = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_books"
    )

    # mapping dữ liệu
    doc_register = models.CharField(max_length=100)

    # tài khoản liên quan
    account_codes = models.JSONField(blank=True, null=True)

    # rule filter
    filter_conditions = models.JSONField(blank=True, null=True)

    # kỳ sổ
    period_type = models.CharField(
        max_length=20,
        choices=[
            ("month","Tháng"),
            ("quarter","Quý"),
            ("year","Năm")
        ],
        default="month"
    )

    # template
    templates = models.ManyToManyField(
        FormTemplate,
        blank=True
    )

    display_order = models.IntegerField(default=0)

    is_default = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"
