from django import forms
from knowledge_base.models import LegalDocument
from webshell.models import WebProduct, GuideArticle, LandingSection, WebContent


class LegalUploadForm(forms.ModelForm):
    class Meta:
        model = LegalDocument
        fields = "__all__"

        labels = {
            "title": "Tiêu đề văn bản",
            "code": "Số hiệu",
            "document_type": "Loại văn bản",
            "issued_date": "Ngày ban hành",
            "effective_from": "Có hiệu lực từ",
            "effective_to": "Hết hiệu lực",
            "file": "Tệp văn bản",
            "supersedes": "Thay thế văn bản",
            "is_active": "Đang áp dụng",
        }

        help_texts = {
            "code": "Ví dụ: 200/2014/TT-BTC",
            "effective_from": "Để trống nếu có hiệu lực ngay",
            "effective_to": "Để trống nếu chưa có ngày hết hiệu lực",
            "supersedes": "Chọn nếu văn bản này thay thế văn bản khác",
        }

        widgets = {
            "issued_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "effective_from": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "effective_to": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nhập tiêu đề..."}
            ),
            "code": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ví dụ: 01/2025/NĐ-CP"}
            ),
            "document_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "file": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "supersedes": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

class WebProductForm(forms.ModelForm):
    class Meta:
        model = WebProduct
        fields = "__all__"
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control"}),
        }

class GuideArticleForm(forms.ModelForm):
    class Meta:
        model = GuideArticle
        fields = "__all__"
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "video_url": forms.URLInput(attrs={"class": "form-control"}),
        }

class LandingSectionForm(forms.ModelForm):
    class Meta:
        model = LandingSection
        fields = "__all__"
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }

class WebContentForm(forms.ModelForm):
    class Meta:
        model = WebContent
        fields = ["title", "content", "is_active"]