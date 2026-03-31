from django.db import models
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
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    content = CKEditor5Field("Content", config_name="default")
    video_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

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


