from django import forms
from .models import ConsultationRequest


class ConsultationRequestForm(forms.ModelForm):

    class Meta:
        model = ConsultationRequest
        fields = [
            "full_name",
            "phone",
            "email",
            "business_type",
            "company_size",
            "note",
        ]

        widgets = {
            "full_name": forms.TextInput(attrs={
                "placeholder": "Nguyễn Văn A"
            }),
            "phone": forms.TextInput(attrs={
                "placeholder": "0909xxxxxx"
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "example@email.com"
            }),
            "company_size": forms.TextInput(attrs={
                "placeholder": "Ví dụ: 5-10 nhân sự"
            }),
            "note": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Mô tả nhu cầu của bạn..."
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Thêm class Bootstrap cho tất cả field
        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "form-control"
            })