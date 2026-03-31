from django.contrib import admin
from django.utils.html import format_html

from .extract_utils import extract_form_template_data

from .models import DocumentMetadata, DocumentGroup, GroupDocument, FormTemplate, RegisterMapping


# ------------------------------
# Helper: paths Tesseract / Poppler (tuỳ môi trường)
# ------------------------------
# Nếu bạn đặt cấu hình khác trên server, chỉnh lại các đường dẫn này trong settings hoặc ở đây.
# TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# TESSDATA_PREFIX = r"C:\Program Files\Tesseract-OCR\tessdata"
# POPPLER_PATH = r"C:\poppler-25.07.0\Library\bin"



@admin.register(DocumentMetadata)
class DocumentMetadataAdmin(admin.ModelAdmin):
    list_display = ("id", "file_name", "user", "doc_type", "doc_no", "doc_date", "status")
    list_filter = ("doc_type", "status", "upload_date")
    search_fields = ("file_name", "original_filename", "doc_no", "tax_code")


@admin.register(DocumentGroup)
class DocumentGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "group_name", "group_type", "user", "created_at")
    search_fields = ("group_name", "group_code")


@admin.register(GroupDocument)
class GroupDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "group", "document", "role", "added_at")


@admin.register(FormTemplate)
class FormTemplateAdmin(admin.ModelAdmin):
    """
    Admin cho FormTemplate:
    - preview PDF (link)
    - preview thumbnail image
    - preview OCR (chỉ khi obj.pk và pdf_file tồn tại)
    - get_form: auto-extract example_text, keywords, structure_json sau khi upload PDF
    """

    # ====== hiển thị danh sách ======
    list_display = (
        'code', 'name', 'category', 'regulation_source',
        'version', 'is_active', 'confidence_threshold', 'created_by', 'updated_at'
    )
    list_filter = ('category', 'regulation_source', 'is_active')
    search_fields = ('code', 'name', 'title', 'keywords', 'code_norm', 'title_norm', 'keywords_norm')
    ordering = ('code',)

    # ====== ====== Methods (phải có trước khi dùng trong readonly_fields) ======
    def pdf_preview(self, obj):
        """Trả về link mở PDF trong tab mới (nếu có)."""
        if obj and obj.pdf_file:
            try:
                return format_html(
                    '<a href="{}" target="_blank" style="background:#4CAF50;color:white;'
                    'padding:6px 10px;border-radius:4px;text-decoration:none;">📄 Mở PDF</a>',
                    obj.pdf_file.url
                )
            except Exception:
                return "Không thể hiển thị PDF (kiểm tra MEDIA_URL/MEDIA_ROOT)."
        return "Chưa có file PDF."
    pdf_preview.short_description = "📄 Xem trước PDF"

    def image_preview_display(self, obj):
        """Hiển thị thumbnail nếu có."""
        if obj and obj.image_preview:
            try:
                return format_html(
                    '<img src="{}" style="max-width:400px; height:auto; border:1px solid #ccc; border-radius:8px;"/>',
                    obj.image_preview.url
                )
            except Exception:
                return "Không thể hiển thị ảnh (kiểm tra MEDIA)."
        return "Chưa có ảnh xem trước."
    image_preview_display.short_description = "🖼️ Xem trước ảnh"

    def ocr_preview(self, obj):
        if not obj or not obj.pk or not obj.pdf_file:
            return "OCR sẽ hiển thị sau khi lưu."

        try:
            from .services.ocr_service import preview_ocr
            text = preview_ocr(obj.pdf_file.path)
            safe_text = text[:3000].replace("\n", "<br>")
            return format_html(
                "<div style='background:#fafafa;border:1px solid #ddd;padding:10px;"
                "font-family:monospace'>{}</div>",
                safe_text
            )
        except Exception as e:
            return format_html(f"<b style='color:red;'>❌ Lỗi OCR:</b> {e}")

    ocr_preview.short_description = "🔍 Xem trước OCR"

    # ====== readonly_fields (chỉ sau khi method được định nghĩa) ======
    readonly_fields = (
        'created_at', 'updated_at',
        'pdf_preview', 'image_preview_display', 'ocr_preview',
        'code_norm', 'title_norm', 'keywords_norm'
    )

    # ====== Fieldsets groups ======
    fieldsets = (
        ("1️⃣ Thông tin cơ bản", {
            "fields": (
                'code', 'name', 'title', 'description',
                'regulation_source', 'version', 'category',
                'confidence_threshold',
            )
        }),
        ("2️⃣ File mẫu lưu cục bộ", {
            "fields": (
                'pdf_file', 'pdf_preview',
                'docx_file',
                'image_preview', 'image_preview_display'
            ),
            "description": "Upload file PDF / DOCX / Ảnh gốc của biểu mẫu."
        }),
        ("3️⃣ Cấu trúc nhận diện / trích xuất", {
            "fields": (
                'structure_json', 'example_text', 'keywords', 'ocr_preview'
            ),
            "description": "Khai báo cấu trúc JSON, nội dung OCR mẫu và tập từ khóa nhận diện biểu mẫu."
        }),
        ("4️⃣ Tiền xử lý / Normalize (tự động sinh)", {
            "fields": (
                'code_norm', 'title_norm', 'keywords_norm',
            ),
            "description": "Các trường được sinh tự động để phục vụ AI matching."
        }),
        ("5️⃣ Nhóm lưu chứng từ trên Drive", {
            "fields": ('drive_group_path',)
        }),
        ("6️⃣ Quản trị", {
            "fields": (
                'is_active', 'created_by',
                'created_at', 'updated_at'
            )
        }),
    )

    # ====== Tùy chỉnh widget cho các textbox lớn ======
    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'structure_json':
            try:
                formfield.widget.attrs['style'] = 'width:98%; height:320px; font-family:monospace;'
            except Exception:
                pass
        elif db_field.name == 'example_text':
            try:
                formfield.widget.attrs['style'] = 'width:98%; height:220px; font-family:monospace;'
            except Exception:
                pass
        elif db_field.name == 'keywords':
            try:
                formfield.widget.attrs['style'] = 'width:98%; height:100px; font-family:monospace;'
            except Exception:
                pass
        return formfield

    # ====== Khi lưu model từ admin (hook) ======
    def save_model(self, request, obj, form, change):
        """
        - gọi super().save_model để lưu model (vì model.save đã xử lý normalize + tạo thumbnail)
        - nếu upload PDF mới (hoặc example_text rỗng) -> gọi extract_form_template_data
        - lưu update_fields để tránh vòng lặp
        """
        # Lưu object trước (model.save sẽ normalize & có thể tạo thumbnail)
        super().save_model(request, obj, form, change)

        # Nếu object đã có file PDF và chưa có example_text -> try extract
        try:
            if obj.pdf_file and (not obj.example_text or not obj.structure_json):
                # IMPORTANT: dùng path file đã lưu trên disk
                result = extract_form_template_data(obj.pdf_file.path)
                obj.example_text = result.get("example_text", obj.example_text)
                obj.keywords = result.get("keywords", obj.keywords)
                # ensure structure_json is parsed JSON (string -> dict handled inside extract_form_template_data)
                try:
                    structure = result.get("structure_json", None)
                    # if structure is a JSON string, try to load it
                    if isinstance(structure, str):
                        import json as _json
                        obj.structure_json = _json.loads(structure)
                    else:
                        obj.structure_json = structure
                except Exception:
                    # fallback: keep existing
                    pass

                # Lưu các trường đã cập nhật
                obj.save(update_fields=['example_text', 'keywords', 'structure_json', 'updated_at'])
                print(f"✅ [Admin] Auto-extract template data for {obj.code}")
        except Exception as e:
            # Không raise lỗi để user vẫn có thể lưu mẫu; chỉ log
            print(f"❌ [Admin] Error auto-extracting template data: {e}")

    # ====== Khi lấy form (render form), tránh auto-OCR lúc tạo mới (obj is None) ======
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Không thực hiện extract ở đây để tránh path chưa tồn tại khi tạo mới.
        return form


@admin.register(RegisterMapping)
class RegisterMappingAdmin(admin.ModelAdmin):
    list_display = ("id", "plan_code", "flow", "form_template", "is_active")
