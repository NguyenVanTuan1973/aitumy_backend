from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

# Hỗ trợ thay thế văn bản, Hỗ trợ hiệu lực theo thời gian
class LegalDocument(models.Model):
    DOCUMENT_TYPE = [
        ("thong_tu", "Thông tư"),
        ("nghi_dinh", "Nghị định"),
        ("chuan_muc", "Chuẩn mực"),
        ("luat", "Luật"),
    ]

    title = models.CharField(max_length=500)
    code = models.CharField(max_length=100)  # 200/2014/TT-BTC
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE)

    issued_date = models.DateField()
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)

    file = models.FileField(upload_to="knowledge/legal/raw/")

    supersedes = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.title}"

class LegalClause(models.Model):
    document = models.ForeignKey(
        LegalDocument, on_delete=models.CASCADE, related_name="clauses"
    )

    chapter = models.CharField(max_length=50, blank=True)
    article = models.CharField(max_length=50)  # Điều
    clause = models.CharField(max_length=50, blank=True)  # Khoản
    point = models.CharField(max_length=50, blank=True)  # Điểm

    title = models.CharField(max_length=500, blank=True)
    content = models.TextField()

    topic = models.CharField(max_length=200, blank=True, db_index=True)

    metadata = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["topic"]),
            models.Index(fields=["article"]),
        ]

    def __str__(self):
        return f"{self.document.code} - Điều {self.article}"

class AccountingRegime(models.Model):
    code = models.CharField(max_length=50)  # 152/2025/TT-BTC, 99/2025/TT-BTC
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.code

# Hệ thống tài khoản kế toán theo từng chế độ
class AccountChart(models.Model):
    regime = models.ForeignKey(AccountingRegime, on_delete=models.CASCADE)

    account_code = models.CharField(max_length=20)  # 111, 112
    account_name = models.CharField(max_length=255)

    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL
    )

    account_type = models.CharField(max_length=50, blank=True)

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("regime", "account_code")

    def __str__(self):
        return f"{self.account_code} - {self.account_name}"

# lớp AI dùng để gợi ý định khoản
class AccountingRule(models.Model):
    regime = models.ForeignKey(AccountingRegime, on_delete=models.CASCADE)

    rule_code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)

    description = models.TextField()

    debit_accounts = models.ManyToManyField(
        AccountChart, related_name="debit_rules"
    )
    credit_accounts = models.ManyToManyField(
        AccountChart, related_name="credit_rules"
    )

    legal_clauses = models.ManyToManyField(LegalClause, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class KnowledgeIndex(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    text_content = models.TextField()
    embedding = models.JSONField()

    keywords = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

class BusinessSector(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    # Liên kết trực tiếp đến văn bản gốc mô tả ngành
    legal_clauses = models.ManyToManyField(
        LegalClause,
        blank=True,
        related_name="related_sectors"
    )

    metadata = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class TaxPolicy(models.Model):

    PLAN_TYPES = [
        ("HKD_PLUS", "HKD Thuế khoán % doanh thu"),
        ("HKD_PRO", "HKD Kê khai khấu trừ"),
    ]

    sector = models.ForeignKey(
        BusinessSector,
        on_delete=models.CASCADE,
        related_name="tax_policies"
    )

    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)

    # HKD_PLUS dùng %
    vat_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    pit_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    # HKD_PRO có thể dùng công thức
    tax_formula = models.TextField(blank=True)

    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    legal_clauses = models.ManyToManyField(
        LegalClause,
        blank=True,
        related_name="tax_policies"
    )

    notes = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-effective_from"]

    def __str__(self):
        return f"{self.sector.name} - {self.plan_type}"

