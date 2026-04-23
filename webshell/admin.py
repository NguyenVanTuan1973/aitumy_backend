from django.contrib import admin
from django.utils.html import format_html

from .models import WebContent, GuideArticle, FAQCategory, FAQItem, ConsultationRequest, WebProduct


@admin.register(WebContent)
class WebContentAdmin(admin.ModelAdmin):
    list_display = ("content_key", "title", "is_active", "updated_at")
    search_fields = ("content_key", "title")
    list_filter = ("is_active",)

# =========================
# WebProduct Admin
# =========================
@admin.register(WebProduct)
class WebProductAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "slug",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "description",
        "slug",
    )

    prepopulated_fields = {
        "slug": ("name",)
    }

    ordering = ("name",)

    list_editable = ("is_active",)

    fieldsets = (
        ("Thông tin sản phẩm", {
            "fields": ("name", "slug", "description")
        }),
        ("Trạng thái", {
            "fields": ("is_active",)
        }),
    )


# =========================
# GuideArticle Admin
# =========================
@admin.register(GuideArticle)
class GuideArticleAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "guide_type",
        "order",
        "is_active",
        "video_preview",
        "created_at",
    )

    list_filter = (
        "guide_type",
        "is_active",
        "created_at",
    )

    search_fields = (
        "title",
        "content",
        "slug",
    )

    ordering = ("order", "-created_at")

    list_editable = (
        "order",
        "is_active",
    )

    prepopulated_fields = {
        "slug": ("title",)
    }

    readonly_fields = (
        "created_at",
        "video_preview",
        "thumbnail_preview",
    )

    fieldsets = (
        ("Thông tin chính", {
            "fields": ("title", "slug", "guide_type", "content")
        }),
        ("Media", {
            "fields": ("video_url", "video_preview", "thumbnail", "thumbnail_preview")
        }),
        ("Hiển thị", {
            "fields": ("order", "is_active", "created_at")
        }),
    )

    # =========================
    # Preview Video Embed
    # =========================
    def video_preview(self, obj):
        embed_url = obj.get_youtube_embed()
        if not embed_url:
            return "Không có video"

        return format_html(
            '<iframe width="300" height="170" src="{}" frameborder="0" allowfullscreen></iframe>',
            embed_url
        )

    video_preview.short_description = "Xem video"

    # =========================
    # Thumbnail preview
    # =========================
    def thumbnail_preview(self, obj):
        thumb = obj.get_youtube_thumbnail()
        if not thumb:
            return "Không có thumbnail"

        return format_html(
            '<img src="{}" width="200" style="border-radius:8px;" />',
            thumb
        )

    thumbnail_preview.short_description = "Thumbnail"

# =========================
# ConsultationRequest Admin
# =========================
@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):

    list_display = (
        "full_name",
        "phone",
        "email",
        "business_type",
        "is_contacted",
        "created_at",
    )

    list_filter = (
        "business_type",
        "is_contacted",
        "created_at",
    )

    search_fields = (
        "full_name",
        "phone",
        "email",
    )

    ordering = ("-created_at",)

    readonly_fields = ("created_at",)

    actions = ["mark_as_contacted", "mark_as_not_contacted"]

    def mark_as_contacted(self, request, queryset):
        queryset.update(is_contacted=True)
    mark_as_contacted.short_description = "Đánh dấu đã liên hệ"

    def mark_as_not_contacted(self, request, queryset):
        queryset.update(is_contacted=False)
    mark_as_not_contacted.short_description = "Đánh dấu chưa liên hệ"


# =========================
# FAQCategory Admin
# =========================
@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "order",
        "faq_count",
    )

    search_fields = ("name",)

    ordering = ("order", "name")

    def faq_count(self, obj):
        return obj.faqs.count()
    faq_count.short_description = "Số FAQ"


# =========================
# FAQItem Admin
# =========================
class FAQItemAdmin(admin.ModelAdmin):

    list_display = (
        "question",
        "category",
        "order",
        "is_active",
    )

    list_filter = (
        "category",
        "is_active",
    )

    search_fields = (
        "question",
        "answer",
    )

    ordering = ("category", "order")

    list_editable = (
        "order",
        "is_active",
    )

    filter_horizontal = ("legal_clauses",)

    fieldsets = (
        ("Thông tin chính", {
            "fields": ("category", "question", "answer")
        }),
        ("Liên kết & hiển thị", {
            "fields": ("legal_clauses", "order", "is_active")
        }),
    )


admin.site.register(FAQItem, FAQItemAdmin)