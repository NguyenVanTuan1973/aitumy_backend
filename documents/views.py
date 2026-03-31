import os
import traceback
from django.conf import settings
from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.authentication import JWTAuthentication

from .cleanup.export_file_cleanup import cleanup_export_files
from .serializers import DocumentUploadSerializer, DocumentMetadataSerializer, DocumentGroupCreateSerializer, DocumentGroupSerializer
from .models import DocumentMetadata, DocumentGroup, GroupDocument, FormTemplate
from django.shortcuts import get_object_or_404

from .services.export.export_pdf_by_type import export_pdf_by_type, ReportType
from .tasks import process_document_task
from django.core.files.storage import default_storage
from django.db import transaction

from .extract_utils import extract_and_parse, extract_from_pdf, extract_text_auto, generate_pdf_thumbnail, \
    generate_image_thumbnail

from .recognize_utils import recognize_document
from rest_framework.permissions import AllowAny, IsAuthenticated  # Tạm để test


from users.models import OrganizationMember, DriveFolder, UserDrive


class DocumentRecognizeAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        files = serializer.validated_data["files"]

        # 🔥 LẤY doc_type TỪ FLUTTER (CHÍNH LÀ code_norm)
        doc_type = request.data.get("doc_type")

        form_template = None
        structure_json = None
        drive_group_path = None
        confidence_threshold = None

        # 🔎 Lookup FormTemplate
        if doc_type:
            doc_type_norm = doc_type.lower().strip()

            form_template = FormTemplate.objects.filter(
                is_active=True,
                code_norm=doc_type_norm
            ).first()

            if form_template:
                structure_json = form_template.structure_json
                drive_group_path = form_template.drive_group_path
                confidence_threshold = form_template.confidence_threshold

        preview_results = []

        for f in files:
            # 1️⃣ Lưu file tạm
            temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
            os.makedirs(temp_dir, exist_ok=True)

            temp_path = os.path.join(temp_dir, f.name)
            saved_path = default_storage.save(temp_path, f)
            full_path = default_storage.path(saved_path)

            # 2️⃣ OCR + nhận diện
            result = recognize_document(full_path)

            if not result["ocr_text"].strip():
                return Response(
                    {"error": f"Không thể OCR file {f.name}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 🔐 CHECK CONFIDENCE (AN TOÀN AI)
            if form_template and confidence_threshold is not None:
                if result["score"] < confidence_threshold:
                    structure_json = None

            # 2a️⃣ Tạo thumbnail
            thumbnail_rel_path = None
            ext = os.path.splitext(f.name)[1].lower()

            try:
                if ext == ".pdf":
                    thumbnail_rel_path = generate_pdf_thumbnail(full_path, f.name)
                elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
                    thumbnail_rel_path = generate_image_thumbnail(full_path)
            except Exception as e:
                print(f"⚠️ Lỗi tạo thumbnail: {e}")

            # 3️⃣ Preview trả Flutter
            preview_results.append({
                "temp_file_path": saved_path,
                "file_name": f.name,

                # --- AI detect ---
                "template": result["template"],
                "form_code": result["form_code"],
                "score": result["score"],

                # --- OCR ---
                "metadata": result["metadata"],
                "ocr_text": result["ocr_text"][:1000],

                # --- UI ---
                "thumbnail_url": thumbnail_rel_path,

                # 🔥 FORM TEMPLATE DATA
                "doc_type": doc_type,
                "structure_json": structure_json,
                "drive_group_path": drive_group_path,
            })

        return Response({
            "message": "Nhận diện thành công.",
            "previews": preview_results
        }, status=status.HTTP_200_OK)

class DocumentSaveAPIView(APIView):
    """
    💾 Bước 2: Lưu chứng từ & metadata vào DB + Upload Drive
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        temp_file_path = data.get("temp_file_path")
        fields = data.get("fields", {})
        user = request.user if request.user.is_authenticated else None

        if not temp_file_path or not default_storage.exists(temp_file_path):
            return Response({"error": "Không tìm thấy file tạm"}, status=400)

        full_path = default_storage.path(temp_file_path)
        file_name = os.path.basename(full_path)
        file_size = os.path.getsize(full_path)

        try:
            doc = DocumentMetadata.objects.create(
                user=user,
                original_filename=file_name,
                file_name=file_name,
                file_format=file_name.split('.')[-1].lower(),
                file_size=file_size,
                status='saved',
                doc_type=fields.get('doc_type'),
                doc_no=fields.get('doc_no'),
                tax_code=fields.get('tax_code'),
                description=fields.get('description'),
                total_amount=fields.get('total_amount'),
                tax_amount=fields.get('tax_amount'),
                extract_log=fields.get('log', {}),
                ocr_text=fields.get('ocr_text', ''),
            )

            # Gửi tác vụ nền upload Google Drive
            process_document_task.delay(doc.id, temp_file_path)

            return Response({
                "message": "Lưu chứng từ thành công!",
                "document": DocumentMetadataSerializer(doc).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": f"Lỗi khi lưu chứng từ: {e}"}, status=500)

class DocumentUploadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        files = serializer.validated_data['files']
        user = request.user
        created = []

        for f in files:
            # 1️⃣ Lưu file tạm trên server
            save_path = f"documents/uploads/{user.id}/{f.name}"
            path = default_storage.save(save_path, f)
            full_path = default_storage.path(path)

            # 👉 Gọi extract trước khi upload
            extracted_text = extract_from_pdf(full_path)

            # 2️⃣ Gọi hàm trích xuất OCR + parse
            extract_result = extract_and_parse(full_path)
            ocr_text = extract_result.get("ocr_text", "")
            fields = extract_result.get("fields", {})
            log = extract_result.get("log", {})

            # 3️⃣ Tạo record metadata trong DB
            doc = DocumentMetadata.objects.create(
                user=user,
                original_filename=f.name,
                file_name=f.name,
                file_format=f.name.split('.')[-1].lower(),
                file_size=f.size if hasattr(f, 'size') else None,
                status='pending',
                tax_code=fields.get('tax_code'),
                doc_no=fields.get('doc_no'),
                doc_date=fields.get('doc_date'),
                total_amount=fields.get('total_amount'),
                extract_log=log
            )

            # 4️⃣ Gửi tác vụ nền upload lên Google Drive
            process_document_task.delay(doc.id, path)

            created.append(DocumentMetadataSerializer(doc).data)

        return Response({"created": created}, status=status.HTTP_201_CREATED)

class DocumentListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = DocumentMetadata.objects.filter(user=request.user).order_by("-upload_date")
        ser = DocumentMetadataSerializer(qs, many=True)
        return Response(ser.data)

class CreateGroupAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DocumentGroupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            group = DocumentGroup.objects.create(
                user=request.user,
                group_code=data.get('group_code') or None,
                group_name=data['group_name'],
                group_type=data.get('group_type') or None,
                notes=data.get('notes') or ''
            )
        docs = data.get('documents') or []
        for d in docs:
            doc_obj = get_object_or_404(DocumentMetadata, id=d['id'], user=request.user)
            GroupDocument.objects.create(group=group, document=doc_obj, role=d.get('role', 'support'))
        return Response(DocumentGroupSerializer(group).data, status=status.HTTP_201_CREATED)

class DocumentDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        doc = get_object_or_404(DocumentMetadata, id=pk, user=request.user)
        return Response(DocumentMetadataSerializer(doc).data)

class ExportFilePdfView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        cleanup_export_files()

        user = request.user
        report_type = request.data.get("reportTypeExport")
        organization_id = request.data.get("organization_id")
        params = request.data.get("params", {})

        # =============================
        # 1️⃣ Validate report type
        # =============================
        if not report_type:

            return Response(
                {"message": "Thiếu reportTypeExport"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            report_enum = ReportType(report_type)

        except ValueError:

            return Response(
                {
                    "message": f"reportTypeExport không hợp lệ: {report_type}",
                    "supported": ReportType.values(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # =============================
        # 2️⃣ FREE user
        # =============================
        if not organization_id:

            if report_enum not in {
                ReportType.INDIVIDUAL_INCOME,
                ReportType.INDIVIDUAL_EXPENSE,
                ReportType.ACCOUNTING_REGISTER,
            }:

                return Response(
                    {"message": "User FREE không được export loại báo cáo này"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            organization = None

        # =============================
        # 3️⃣ Organization flow
        # =============================
        else:

            try:
                membership = OrganizationMember.objects.select_related(
                    "organization"
                ).get(
                    user=user,
                    organization_id=organization_id,
                    is_active=True,
                )

            except OrganizationMember.DoesNotExist:

                return Response(
                    {"message": "Bạn không thuộc Organization này"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            organization = membership.organization


            if not organization.can_export_report(report_enum):

                return Response(
                    {"message": "Organization không được export loại báo cáo này"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # =============================
        # 4️⃣ Export PDF (FULL DEBUG)
        # =============================
        try:

            pdf_path = export_pdf_by_type(
                report_type=report_enum,
                user=user,
                organization=organization,
                params=params,
            )

        except ValueError as e:

            traceback.print_exc()
            return Response(
                {"message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:

            traceback.print_exc()
            return Response(
                {
                    "message": "Lỗi export PDF",
                    "detail": str(e),
                    "error_type": type(e).__name__,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # =============================
        # 5️⃣ Check file exists
        # =============================

        if not pdf_path:

            return Response(
                {"message": "pdf_path trả về None"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not os.path.exists(pdf_path):

            return Response(
                {"message": "Không tìm thấy file PDF"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return FileResponse(
            open(pdf_path, "rb"),
            as_attachment=True,
            filename=os.path.basename(pdf_path),
            content_type="application/pdf",
        )

