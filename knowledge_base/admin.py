from django.contrib import admin
from .models import LegalDocument, LegalClause, AccountingRegime, AccountChart, AccountingRule, KnowledgeIndex


# Register your models here.
@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "document_type", "is_active")
    search_fields = ("title", "code")
    list_filter = ("is_active",)

@admin.register(LegalClause)
class LegalClauseAdmin(admin.ModelAdmin):
    list_display = ("title", "document", "chapter", "article", "clause", "point", "content", "topic", "metadata", "is_active")
    search_fields = ("title", "article")
    list_filter = ("is_active",)

@admin.register(AccountingRegime)
class AccountingRegimeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "description")


@admin.register(AccountChart)
class AccountChartAdmin(admin.ModelAdmin):
    list_display = ("regime", "account_code", "account_name", "parent", "account_type", "description")

@admin.register(AccountingRule)
class AccountingRuleAdmin(admin.ModelAdmin):
    list_display = ("regime", "rule_code", "name", "description")

@admin.register(KnowledgeIndex)
class KnowledgeIndexAdmin(admin.ModelAdmin):
    list_display = ("content_type", "object_id", "content_object", "text_content", "embedding", "keywords")