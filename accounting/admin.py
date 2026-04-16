from django.contrib import admin

from .models import Regulation, Account, AccountType


# Register your models here.
@admin.register(Regulation)
class RegulationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "effective_date")

# @admin.register(AccountType)
# class AccountTypeAdmin(admin.ModelAdmin):
#     list_display = ("__all__")

@admin.register(Account)
class AccountTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "regulation", "name", "parent", "level", "account_type", "normal_balance")