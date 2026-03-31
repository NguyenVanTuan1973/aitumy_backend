from django.db import models
from django.core.exceptions import ValidationError

class Regulation(models.Model):
    """
    Thông tư / Chuẩn mực kế toán
    Ví dụ: 99/2025/TT-BTC
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    effective_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.code


class AccountType(models.TextChoices):
    ASSET = "asset", "Tài sản"
    LIABILITY = "liability", "Nợ phải trả"
    EQUITY = "equity", "Vốn chủ sở hữu"
    REVENUE = "revenue", "Doanh thu"
    EXPENSE = "expense", "Chi phí"
    INCOME_OTHER = "income_other", "Thu nhập khác"
    EXPENSE_OTHER = "expense_other", "Chi phí khác"
    RESULT = "result", "Xác định kết quả"


class Account(models.Model):

    regulation = models.ForeignKey(
        Regulation,
        on_delete=models.CASCADE,
        related_name="accounts"
    )

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,   # ✅ đổi CASCADE
        null=True,
        blank=True,
        related_name="children"
    )

    level = models.PositiveSmallIntegerField(default=1)

    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices
    )

    normal_balance = models.CharField(
        max_length=10,
        choices=(
            ("debit", "Dư Nợ"),
            ("credit", "Dư Có"),
        ),
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("regulation", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def is_root(self):
        return self.parent is None

    def get_full_path(self):
        if self.parent:
            return f"{self.parent.code} > {self.code}"
        return self.code

    def clean(self):
        if self.parent:
            if self.parent == self:
                raise ValidationError("Tài khoản không thể là cha của chính nó.")

            parent = self.parent
            while parent:
                if parent == self:
                    raise ValidationError("Không được tạo vòng lặp cây tài khoản.")
                parent = parent.parent

    def save(self, *args, **kwargs):
        self.full_clean()

        if self.parent:
            self.level = self.parent.level + 1
        else:
            self.level = 1

        super().save(*args, **kwargs)

