from django.contrib import admin
from .models import WebContent


@admin.register(WebContent)
class WebContentAdmin(admin.ModelAdmin):
    list_display = ("content_key", "title", "is_active", "updated_at")
    search_fields = ("content_key", "title")
    list_filter = ("is_active",)