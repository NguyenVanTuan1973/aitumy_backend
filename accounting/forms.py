from django import forms
from .models import Regulation, Account


class RegulationForm(forms.ModelForm):
    class Meta:
        model = Regulation
        fields = ["code", "name", "effective_date"]


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            "regulation",
            "code",
            "name",
            "parent",
            "account_type",
            "normal_balance",
            "is_active",
        ]