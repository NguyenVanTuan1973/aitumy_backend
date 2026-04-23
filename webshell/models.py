import re

from django.db import models
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field


# Chính sách & điều khoản
class LandingSection(models.Model):
    title = models.CharField(max_length=255)
    content = CKEditor5Field("Content", config_name="default")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

# Sản phẩm & gói dịch vụ
class WebProduct(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True)

# Trung tâm hướng dẫn
class GuideArticle(models.Model):
    GUIDE_TYPE_CHOICES = (
        ("video", "Video Guide"),
        ("article", "Article Guide"),
    )

    title = models.CharField(max_length=255)

    slug = models.SlugField(unique=True, blank=True)

    guide_type = models.CharField(
        max_length=20,
        choices=GUIDE_TYPE_CHOICES,
        default="video",
        db_index=True
    )

    content = CKEditor5Field("Content", config_name="default", blank=True)

    video_url = models.URLField(blank=True)

    thumbnail = models.URLField(blank=True)

    order = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title

    # 👉 Auto slug nếu không nhập
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    # 👉 Lấy embed YouTube
    def get_youtube_embed(self):
        if not self.video_url:
            return None

        url = str(self.video_url)

        match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)

        if not match:
            return None

        video_id = match.group(1)

        return f"https://www.youtube.com/embed/{video_id}"

    # 👉 Lấy thumbnail YouTube (auto)
    def get_youtube_thumbnail(self):
        if not self.video_url:
            return None

        match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", self.video_url)

        if not match:
            return None

        video_id = match.group(1)

        return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

class WebContent(models.Model):

    CONTENT_TYPE_CHOICES = [
        ("landing", "Landing Page"),        # Trang đích
        ("privacy", "Privacy Policy"),      # Chính sách bảo mật
        ("terms", "Terms of Use"),          # Điều khoản Sử dụng
        ("pricing", "Pricing"),             # Bảng giá dịch vụ
        ("about", "About Us"),              # Về Chúng Tôi
        ("faq", "FAQ"),                     # Câu hỏi thường gặp
    ]

    content_key = models.CharField(
        max_length=50,
        choices=CONTENT_TYPE_CHOICES,
        unique=True
    )

    title = models.CharField(max_length=255)

    content = CKEditor5Field("Content", config_name="default")

    is_active = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_content_key_display()} - {self.title}"

# Lưu yêu cầu tư vấn của khách hàng
class ConsultationRequest(models.Model):

    BUSINESS_TYPE_CHOICES = [
        ("household", "Hộ kinh doanh"),
        ("company_small", "Doanh nghiệp nhỏ"),
        ("company_medium", "Doanh nghiệp vừa"),
        ("company_large", "Doanh nghiệp lớn"),
        ("service_accounting", "Dịch vụ kế toán"),
        ("other", "Khác"),
    ]

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPE_CHOICES)
    company_size = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)

    is_contacted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.phone}"

# Hệ thống phân loại câu hỏi đã có sẵn
class FAQCategory(models.Model):
    name = models.CharField(max_length=100)
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class FAQItem(models.Model):
    category = models.ForeignKey(
        FAQCategory,
        on_delete=models.CASCADE,
        related_name="faqs"
    )

    question = models.CharField(max_length=255)
    answer = CKEditor5Field("Answer", config_name="default")

    legal_clauses = models.ManyToManyField(
        "knowledge_base.LegalClause",
        blank=True,
        related_name="faq_items"
    )

    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.question


