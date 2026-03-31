import io
import json
import requests

import datetime

from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.utils.encoding import force_str
from django.views.decorators.csrf import csrf_exempt
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseUpload
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from users.utils.google_oauth import exchange_code_for_tokens
from users.models import User, UserDrive, DriveFolder, UserSession
import uuid
import os
from documents.extract_utils import extract_from_pdf
from documents.models import DocumentMetadata

from .serializers import CreateDocumentSerializer
from .services.drive_status_service import DriveStatusService
from .services.drive_workspace_service import DriveWorkspaceService
from .services.get_sheet_data_router import get_sheet_data_by_user, get_user_plan_code
from .services.google_drive_service import init_tumy_structure
from .services.google_oauth_service import GoogleOAuthService
# from .services.google_sheet_header_service import init_sheet_headers
# from .services.google_sheet_get_data_service import ensure_free_user_sheet
from googleapiclient.discovery import build

from .utils.period_utils import get_period_range


class GoogleOAuth2CallbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response(
                {"error": "Thiếu mã code OAuth2"},
                status=400
            )

        user = request.user

        # 1️⃣ Exchange code → token
        tokens = exchange_code_for_tokens(code)

        # 2️⃣ Lưu token (CHỈ TOKEN)
        user_drive, _ = UserDrive.objects.get_or_create(user=user)
        user_drive.access_token = tokens["access_token"]
        user_drive.refresh_token = tokens.get(
            "refresh_token",
            user_drive.refresh_token,
        )
        user_drive.token_expiry = tokens["expiry"]
        user_drive.save(
            update_fields=[
                "access_token",
                "refresh_token",
                "token_expiry",
                "updated_at",
            ]
        )

        # 3️⃣ Xác nhận OAuth session
        session = UserSession.objects.filter(
            user=user,
            action="google_oauth",
        ).order_by("-created_at").first()

        if not session:
            return Response(
                {"error": "OAuth session not found"},
                status=400
            )

        # (OPTIONAL) log mode cho debug
        mode = session.metadata.get("mode")

        # 4️⃣ Kết thúc session
        session.delete()

        return Response({
            "message": "✅ Google OAuth connected",
            "mode": mode,
        })

# GET – Drive Status
class DriveStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        status = DriveStatusService(request.user).get_status()
        return Response({"status": status})

def has_drive_permission(user):
    pass
    """
    Kiểm tra user có được phép dùng Google Drive hay không
    """
    # return UserModule.objects.filter(
    #     user=user,
    #     module__code="google_drive",
    #     is_enabled=True
    # ).exists()

# Lấy Google OAuth URL
class DriveAuthUrlView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        oauth = GoogleOAuthService()
        auth_url = oauth.build_auth_url(
            user=user,
            scopes=[
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/spreadsheets",
            ],
            mode="full_drive",
        )

        return Response({
            "auth_url": auth_url,
        })

class DriveConnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response({"error": "FORBIDDEN"}, status=403)

        mode = request.data.get("mode", "full_drive")

        if mode == "sheet_only":
            return self._connect_sheet_only(request)

        return self._connect_full_drive(request)


    def _connect_full_drive(self, request):
        user = request.user

        drive, _ = UserDrive.objects.get_or_create(user=user)

        if not drive.access_token or not drive.refresh_token:
            return Response(
                {"error": "GOOGLE_NOT_CONNECTED"},
                status=400,
            )

        DriveInitFolderView(user).init()

        return Response({
            "connected": True,
            "mode": "full_drive",
        })

# OAuth Callback (Flutter gửi code)
class DriveOAuthCallbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code")

        if not code:
            return Response(
                {"error": "Missing OAuth code"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1️⃣ Đổi code → token
        tokens = exchange_code_for_tokens(code)

        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")
        expiry = tokens["expiry"]

        # 2️⃣ Lấy email Google (chỉ để hiển thị)
        info = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        google_email = info.json().get("email") if info.status_code == 200 else None

        # 3️⃣ Lưu vào UserDrive (KHÔNG tạo user mới)
        UserDrive.objects.update_or_create(
            user=request.user,
            defaults={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expiry": expiry,
                # drive_folder_id CHƯA có ở đây
            }
        )

        return Response({
            "message": "Google Drive connected",
            "email": google_email
        })

# API TẠO FOLDER DRIVE CHO CẢ APP
class DriveInitFolderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        user = request.user
        organization = getattr(request, "organization", None)

        # ============================================
        # 1️⃣ NHẬN serverAuthCode
        # ============================================
        server_auth_code = request.data.get("server_auth_code")

        if not server_auth_code:
            return Response(
                {"detail": "Missing server_auth_code"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ============================================
        # 2️⃣ EXCHANGE TOKEN VỚI GOOGLE
        # ============================================

        try:
            token_res = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": server_auth_code,
                    "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                    "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                    "redirect_uri": "http://localhost:8000/api/drive/oauth/callback/",
                    "grant_type": "authorization_code",
                },
                timeout=10,
            )

            token_data = token_res.json()

            if "error" in token_data:
                return Response(
                    {
                        "detail": "Google token exchange failed",
                        "error": token_data,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in")

        except Exception as e:
            return Response(
                {"detail": "Token exchange error", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ============================================
        # 3️⃣ TÍNH EXPIRY
        # ============================================
        expiry = None
        if expires_in:
            expiry = timezone.now() + datetime.timedelta(seconds=int(expires_in))

        # ============================================
        # 4️⃣ GIỮ REFRESH TOKEN CŨ (QUAN TRỌNG)
        # ============================================
        existing_drive = UserDrive.objects.filter(user=user).first()

        final_refresh_token = refresh_token or (
            existing_drive.refresh_token if existing_drive else None
        )

        # ============================================
        # 5️⃣ LƯU TOKEN
        # ============================================
        drive, _ = UserDrive.objects.update_or_create(
            user=user,
            defaults={
                "access_token": access_token,
                "refresh_token": final_refresh_token,
                "token_expiry": expiry,
            }
        )

        # ============================================
        # 6️⃣ CHECK STATUS
        # ============================================
        status_service = DriveStatusService(
            user=user,
            organization=organization,
        )

        if status_service.is_initialized():
            return Response(
                status_service.serialize(),
                status=status.HTTP_200_OK,
            )

        # ============================================
        # 7️⃣ INIT WORKSPACE
        # ============================================
        workspace_service = DriveWorkspaceService()

        try:
            workspace = workspace_service.ensure(
                user=user,
                organization=organization,
            )

            return Response(workspace, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    "detail": "Init drive failed",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class CreateDocumentAPIView(APIView):

    permission_classes = [IsAuthenticated]

    DATA_SOURCE_COLUMNS = [
        "doc_date",
        "doc_number",
        "doc_content",
        "unit",
        "quantity",
        "price",
        "total_amount",
        "tax_vat_amount",
        "tax_individual_amount",
        "special_tax_amount",
        "tax_price_per_unit",
        "tax_rate",
        "discount_amount",
        "payment_type",
        "repayment_date",
        "out_in_code",
        "product_code",
        "job_code",
        "industry_code",
        "customer_code",
        "supplier_code",
        "employee_code",
        "bank_code",
        "doc_register",
        "accounting_code",
        "metadata_code",
        "set_id",
        "created_at",
    ]

    # =====================================================
    # UTILITIES
    # =====================================================

    def create_set_id(self):

        now = timezone.now()

        return f"SET{now.strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"

    def create_doc_id(self):

        now = timezone.now()

        return f"DOC_{now.year}_{uuid.uuid4().hex[:6].upper()}"

    def normalize_number(self, value):

        if isinstance(value, str):

            value = value.replace(",", "")

            try:
                return float(value)
            except:
                return value

        return value

    # =====================================================
    # GOOGLE SHEET APPEND
    # =====================================================

    def append_sheet(self, spreadsheet_id, sheet_name, values, token):

        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}:append"

        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            params={
                "valueInputOption": "USER_ENTERED",
                "insertDataOption": "INSERT_ROWS",
            },
            json={"values": values},
            timeout=15,
        )

        return resp

    # =====================================================
    # DRIVE UTILITIES
    # =====================================================

    def ensure_folder(self, service, name, parent_id=None):

        query = f"name='{name}' and trashed=false"

        if parent_id:
            query += f" and '{parent_id}' in parents"

        result = service.files().list(
            q=query,
            fields="files(id,name)",
        ).execute()

        if result["files"]:
            return result["files"][0]["id"]

        body = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_id:
            body["parents"] = [parent_id]

        folder = service.files().create(
            body=body,
            fields="id",
        ).execute()

        return folder["id"]

    def upload_file(self, service, folder_id, file_obj):

        file_stream = io.BytesIO(file_obj.read())

        media = MediaIoBaseUpload(
            file_stream,
            mimetype=file_obj.content_type,
            resumable=True,
        )

        metadata = {
            "name": file_obj.name,
            "parents": [folder_id],
        }

        result = (
            service.files()
            .create(
                body=metadata,
                media_body=media,
                fields="id,name,webViewLink",
            )
            .execute()
        )

        return result

    # =====================================================
    # POST
    # =====================================================

    def post(self, request):

        payload_raw = request.data.get("payload")

        if not payload_raw:
            return Response(
                {"error": "PAYLOAD_REQUIRED"},
                status=400
            )

        try:
            payload = json.loads(payload_raw)
        except Exception:
            return Response(
                {"error": "PAYLOAD_INVALID_JSON"},
                status=400
            )

        # =====================================================
        # SERIALIZER
        # =====================================================

        serializer = CreateDocumentSerializer(
            data={
                **payload,
                "evidence_file": request.FILES.get("evidence_file")
            }
        )

        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        values = data.get("values", [])

        if not values:
            return Response(
                {"error": "VALUES_EMPTY"},
                status=400
            )

        file_obj = request.FILES.get("evidence_file")

        # =====================================================
        # USER DRIVE
        # =====================================================

        user_drive = getattr(request.user, "drive", None)

        if not user_drive:
            return Response(
                {"error": "NO_GOOGLE_DRIVE_CONNECTED"},
                status=400
            )

        # =====================================================
        # GOOGLE CREDENTIAL
        # =====================================================

        creds = Credentials(
            token=user_drive.access_token,
            refresh_token=user_drive.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        )

        drive_service = build("drive", "v3", credentials=creds)

        # =====================================================
        # GET SPREADSHEET
        # =====================================================

        current_year = timezone.now().year

        try:
            drive_folder = DriveFolder.objects.get(
                drive=user_drive,
                name=f"HKD_DATA_{current_year}",
            )
        except DriveFolder.DoesNotExist:
            return Response(
                {"error": "SHEET_FILE_NOT_FOUND"},
                status=404
            )

        spreadsheet_id = drive_folder.sheet_id

        # =====================================================
        # CREATE IDS
        # =====================================================

        set_id = self.create_set_id()
        doc_id = self.create_doc_id()

        now = timezone.now()

        # =====================================================
        # DRIVE FOLDER STRUCTURE
        # =====================================================

        year = str(now.year)
        month = f"{now.month:02d}"

        year_id = self.ensure_folder(drive_service, year)
        chungtu_id = self.ensure_folder(drive_service, "CHUNG_TU", year_id)
        month_id = self.ensure_folder(drive_service, month, chungtu_id)

        drive_file_id = None
        drive_url = None
        file_name = None
        file_size = None
        mime_type = None

        if file_obj:
            uploaded = self.upload_file(
                drive_service,
                month_id,
                file_obj,
            )

            drive_file_id = uploaded["id"]
            drive_url = uploaded["webViewLink"]
            file_name = uploaded["name"]
            file_size = file_obj.size
            mime_type = file_obj.content_type

        # =====================================================
        # DOCUMENT SET
        # =====================================================

        document_set_row = [[
            set_id,
            data.get("set_name"),
            data.get("doc_date"),
            data.get("doc_content"),
            data.get("total_amount"),
            1,
            month_id,
            "draft",
            now.isoformat(),
            now.isoformat(),
        ]]

        resp = self.append_sheet(
            spreadsheet_id,
            "document_set",
            document_set_row,
            user_drive.access_token,
        )

        if resp.status_code not in (200, 201):
            return Response(
                {
                    "error": "APPEND_DOCUMENT_SET_FAILED",
                    "google_response": resp.text,
                },
                status=400,
            )

        # =====================================================
        # DOCUMENT METADATA
        # =====================================================

        metadata_row = [[
            doc_id,
            data.get("doc_symbol"),
            data.get("doc_type"),
            data.get("doc_number"),
            data.get("doc_date"),
            data.get("doc_content"),
            month,
            data.get("tax_amount"),
            data.get("total_amount"),
            data.get("discount_amount"),
            data.get("tax_rate"),
            data.get("payment_type"),
            data.get("repayment_day"),
            data.get("out_in_code"),
            data.get("industry_code"),
            data.get("doc_register"),
            drive_file_id,
            file_name,
            mime_type,
            file_size,
            month,
            data.get("job_code"),
            data.get("object_code"),
            data.get("accounting_code"),
            set_id,
            "draft",
            now.isoformat(),
            now.isoformat(),
        ]]

        resp = self.append_sheet(
            spreadsheet_id,
            "documents_metadata",
            metadata_row,
            user_drive.access_token,
        )

        if resp.status_code not in (200, 201):
            return Response(
                {
                    "error": "APPEND_METADATA_FAILED",
                    "google_response": resp.text,
                },
                status=400,
            )

        # =====================================================
        # DATA SOURCE
        # =====================================================

        normalized_values = []

        for row in values:

            row_dict = {}

            if isinstance(row, list):

                for idx, col in enumerate(self.DATA_SOURCE_COLUMNS):
                    row_dict[col] = row[idx] if idx < len(row) else 0

            else:

                for col in self.DATA_SOURCE_COLUMNS:
                    row_dict[col] = row.get(col, 0)

            row_dict["metadata_code"] = doc_id
            row_dict["set_id"] = set_id
            row_dict["created_at"] = now.isoformat()

            final_row = []

            for col in self.DATA_SOURCE_COLUMNS:

                value = row_dict.get(col)

                if col in [
                    "doc_content",
                    "unit",
                    "payment_type",
                    "out_in_code",
                    "product_code",
                    "job_code",
                    "industry_code",
                    "customer_code",
                    "supplier_code",
                    "employee_code",
                    "bank_code",
                    "doc_register",
                    "accounting_code",
                ]:
                    final_row.append(value)

                else:
                    final_row.append(self.normalize_number(value))

            normalized_values.append(final_row)

        resp = self.append_sheet(
            spreadsheet_id,
            "data_source",
            normalized_values,
            user_drive.access_token,
        )

        if resp.status_code not in (200, 201):
            return Response(
                {
                    "error": "APPEND_DATA_SOURCE_FAILED",
                    "google_status": resp.status_code,
                    "google_response": resp.text,
                },
                status=400,
            )

        # =====================================================
        # SUCCESS
        # =====================================================

        return Response(
            {
                "message": "Document created successfully",
                "doc_id": doc_id,
                "set_id": set_id,
                "drive_file_id": drive_file_id,
                "drive_url": drive_url,
                "rows_appended": len(normalized_values),
            },
            status=200,
        )


class GetDataSheetAPIView(APIView):
    """
    API dùng chung cho toàn app
    FE chỉ gọi endpoint này, backend tự phân quyền theo user
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        params = request.query_params

        try:
            # ===============================
            # 1️⃣ ENSURE WORKSPACE
            # ===============================
            workspace = DriveWorkspaceService().ensure(user=user)

            spreadsheet_id = workspace["sheet"]["spreadsheet_id"]

            # ===============================
            # 2️⃣ GET DATA FROM SHEET
            # ===============================
            data = get_sheet_data_by_user(
                user=user,
                spreadsheet_id=spreadsheet_id,
                params=params,
            )

            return Response(
                {
                    "success": True,
                    "data": data,
                },
                status=status.HTTP_200_OK
            )


        except Exception as e:
            import traceback
            traceback.print_exc()

            return Response(
                {
                    "success": False,
                    "error": "GET_SHEET_DATA_FAILED",
                    "detail": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST
            )

class DriveDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        UserDrive.objects.filter(user=request.user).delete()
        return Response({"message": "Drive disconnected"})

# =============================
# Helper: normalize date string
# =============================
def normalize_sheet_date(value):
    """
    Chuẩn hoá ISO datetime → yyyy-mm-dd cho Google Sheet
    """
    if isinstance(value, str):
        try:
            return datetime.datetime.fromisoformat(value).date().isoformat()
        except ValueError:
            pass
    return value

# API lấy dữ liệu Sheet
def parse_sheet_date(value):
    if not value:
        return None

    if isinstance(value, datetime.date):
        return value

    if isinstance(value, str):
        value = value.strip()

        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
            try:
                return datetime.datetime.strptime(value, fmt).date()
            except ValueError:
                pass

    return None

class PublicSheetAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:

            # =============================
            # READ INPUT (NO access_token)
            # =============================
            sheet_type = request.data.get("sheet_type")
            period_type = request.data.get("period_type")

            year = request.data.get("year")
            month = request.data.get("month")
            quarter = request.data.get("quarter")

            if not all([sheet_type, period_type, year]):
                return Response(
                    {"error": "Missing required fields"},
                    status=400
                )

            # =============================
            # BUILD anchor_date
            # =============================
            if period_type == "month":
                anchor_date = datetime.date(int(year), int(month), 1)
            elif period_type == "quarter":
                start_month = (int(quarter) - 1) * 3 + 1
                anchor_date = datetime.date(int(year), start_month, 1)
            elif period_type == "year":
                anchor_date = datetime.date(int(year), 1, 1)
            else:
                return Response({"error": "Invalid period_type"}, status=400)

            start_date, end_date = get_period_range(period_type, anchor_date)

            # =============================
            # USER DRIVE (TEST MODE)
            # =============================
            # user_drive = UserDrive.objects.filter(user=request.user).first()

            try:
                user_drive = request.user.drive
            except UserDrive.DoesNotExist:
                user_drive = None

            if not user_drive:

                user_drive = UserDrive.objects.first()

            if not user_drive or not user_drive.access_token:
                return Response(
                    {"error": "NO_GOOGLE_DRIVE_CONNECTED"},
                    status=400
                )

            # =============================
            # DRIVE + SHEET
            # =============================
            sheet_file_name = f"so_thu_chi_hkd_{year}"

            drive_folder = DriveFolder.objects.get(
                drive=user_drive,
                name=sheet_file_name
            )

            sheet_name = {
                "income": "so_doanh_thu",
                "expense": "so_chi_phi",
            }.get(sheet_type)

            if not sheet_name:
                return Response({"error": "Invalid sheet_type"}, status=400)

            # =============================
            # GOOGLE SHEETS
            # =============================
            creds = Credentials(
                token=user_drive.access_token,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )

            service = build("sheets", "v4", credentials=creds)

            result = service.spreadsheets().values().get(
                spreadsheetId=drive_folder.folder_id,
                range=f"{sheet_name}!A:E"
            ).execute()

            rows = result.get("values", [])

            items = []
            total_amount = 0

            for row in rows:
                if len(row) < 3:
                    continue

                row_date = parse_sheet_date(row[0])
                if not row_date:
                    continue

                try:
                    amount = float(row[2])
                except Exception:
                    continue

                if not (start_date <= row_date <= end_date):
                    continue

                total_amount += amount

                items.append({
                    "date": row_date.isoformat(),
                    "description": row[1],
                    "amount": amount,
                })

            # =============================
            # ✅ RESPONSE ĐÚNG FE
            # =============================
            return Response({
                "rows": items,
                "total_amount": total_amount,
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=500
            )

@csrf_exempt
def upload_file_view(request):

    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    try:
        # -------------------------------------------
        # 1) LẤY DỮ LIỆU TỪ FLUTTER
        # -------------------------------------------
        access_token = request.POST.get('access_token')
        metadata_raw = request.POST.get('metadata')
        file = request.FILES.get('file')

        if not metadata_raw:
            return JsonResponse({"error": "Missing metadata"}, status=400)

        metadata_dict = json.loads(metadata_raw)

        # folder dạng: "chung_tu_ke_toan/tien_te"
        folder_path = metadata_dict.get("folder", "")
        folder_name = folder_path.split("/")[-1].strip()

        # -------------------------------------------
        # 2) KIỂM TRA TOKEN GOOGLE
        # -------------------------------------------
        if not access_token or not file:
            return JsonResponse(
                {'error': 'access_token + file are required'},
                status=400
            )

        google_info_url = "https://www.googleapis.com/oauth2/v3/tokeninfo"
        token_check = requests.get(f"{google_info_url}?access_token={access_token}")

        if token_check.status_code != 200:
            return JsonResponse({
                'error': 'Invalid or expired access_token',
                'status': token_check.text
            }, status=401)

        # -------------------------------------------
        # 3) LẤY FOLDER CHA VÀ FOLDER CON TỪ DB
        # -------------------------------------------
        user = request.user if request.user.is_authenticated else None
        user_drive = UserDrive.objects.filter(user=user).first()

        if not user_drive:
            return JsonResponse({"error": "UserDrive not found"}, status=404)

        # Folder cha = chung_tu_ke_toan
        parent_folder_id = user_drive.drive_folder_id

        # Folder con = tien_te, vat_tu, ...
        target_folder = DriveFolder.objects.filter(
            drive=user_drive,
            name=folder_name
        ).first()

        if not target_folder:
            return JsonResponse({
                "error": "DriveFolder not found for name: " + folder_name
            }, status=404)

        sub_folder_id = target_folder.folder_id

        # -------------------------------------------
        # 4) LƯU TẠM FILE
        # -------------------------------------------
        temp_dir = "drive_uploads/temp/"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, file.name)

        with open(temp_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # -------------------------------------------
        # 5) EXTRACT PDF
        # -------------------------------------------
        extracted_text = ""
        if file.name.lower().endswith(".pdf"):
            try:
                extracted_text = extract_from_pdf(temp_path)
            except Exception as e:
                print("⚠️ PDF extract error:", e)

        # -------------------------------------------
        # 6) UPLOAD GOOGLE DRIVE
        #    ✔ chỉ upload vào folder con (sub_folder_id)
        #    ✔ folder cha chỉ dùng lưu DB, không upload vào cha
        # -------------------------------------------
        metadata = {
            "name": file.name,
            "parents": [sub_folder_id]  # Upload đúng folder con
        }

        boundary = uuid.uuid4().hex
        delimiter = f'--{boundary}'
        close_delim = f'--{boundary}--'

        body = (
            f'{delimiter}\r\n'
            'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            f'{json.dumps(metadata)}\r\n'
            f'{delimiter}\r\n'
            f'Content-Type: {file.content_type or "application/octet-stream"}\r\n\r\n'
        ).encode() + open(temp_path, 'rb').read() + f'\r\n{close_delim}'.encode()

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': f'multipart/related; boundary={boundary}'
        }

        upload_url = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart'
        response = requests.post(upload_url, headers=headers, data=body)

        if response.status_code not in [200, 201]:
            return JsonResponse({
                'error': 'Upload to Drive failed',
                'details': response.text
            }, status=500)

        data = response.json()
        file_id = data.get("id")

        # -------------------------------------------
        # 7) LƯU METADATA
        # -------------------------------------------
        doc = DocumentMetadata.objects.create(
            user=user,
            original_filename=metadata_dict.get("file_name"),
            file_name=metadata_dict.get("file_name"),
            file_format=file.content_type,
            file_size=file.size,

            doc_type=metadata_dict.get("template"),
            doc_no=metadata_dict["metadata"].get("doc_no"),
            doc_date=metadata_dict["metadata"].get("doc_date"),
            description=metadata_dict["metadata"].get("title"),
            ocr_text=metadata_dict.get("ocr_text") or extracted_text,

            # GOOGLE DRIVE
            drive_file_id=file_id,
            drive_link=f"https://drive.google.com/file/d/{file_id}/view",

            # Lưu cả đường dẫn đầy đủ
            drive_path=folder_path,

            # ✔ LƯU FOLDER CHA VÀ FOLDER CON
            drive_parent_folder_id=parent_folder_id,
            drive_sub_folder_id=sub_folder_id,

            drive_mime=file.content_type,
        )

        # -------------------------------------------
        # 8) XÓA FILE TẠM
        # -------------------------------------------
        try:
            os.remove(temp_path)
        except:
            pass

        return JsonResponse({
            "message": "Upload thành công",
            "file_id": file_id,
            "folder_parent": parent_folder_id,
            "folder_sub": sub_folder_id,
            "metadata_id": doc.id
        })

    except Exception as e:

        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def create_folder_view(request):

    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        access_token = data.get('access_token')
        id_token = data.get('id_token')

        if not access_token:
            return JsonResponse({'error': 'Missing access_token'}, status=400)

        # =============================
        # 1️⃣ Xác thực người dùng Google
        # =============================
        verify = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if verify.status_code != 200:
            return JsonResponse({'error': 'Invalid access_token'}, status=400)

        user_info = verify.json()
        email = user_info.get("email")


        # =============================
        # 2️⃣ Lấy hoặc tạo User
        # =============================
        user, created = User.objects.get_or_create(email=email)


        drive_api_url = "https://www.googleapis.com/drive/v3/files"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # =============================
        # 3️⃣ Kiểm tra / tạo thư mục gốc
        # =============================
        query = (
            "name='chung_tu_ke_toan' and "
            "mimeType='application/vnd.google-apps.folder' and "
            "'root' in parents and trashed=false"
        )
        search_resp = requests.get(
            f"{drive_api_url}?q={requests.utils.quote(query)}&fields=files(id,name)",
            headers=headers
        )

        if search_resp.status_code == 200 and search_resp.json().get("files"):
            folder = search_resp.json()["files"][0]
            root_folder_id = folder["id"]

        else:
            create_resp = requests.post(
                drive_api_url,
                headers=headers,
                json={
                    "name": "chung_tu_ke_toan",
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": ["root"]
                }
            )
            if create_resp.status_code not in [200, 201]:
                return JsonResponse({'error': 'Failed to create root folder', 'details': create_resp.text}, status=400)
            root_folder_id = create_resp.json()["id"]


        # =============================
        # 4️⃣ Lưu vào UserDrive
        # =============================
        user_drive, _ = UserDrive.objects.update_or_create(
            user=user,
            defaults={
                "drive_folder_id": root_folder_id,
                "access_token": access_token,
                "token_expiry": timezone.now() + timezone.timedelta(hours=1)
            }
        )

        # =============================
        # 5️⃣ Kiểm tra / tạo các thư mục con
        # =============================
        subfolders = [
            "lao_dong_tien_luong",
            "hang_ton_kho",
        ]

        created_folders = []
        for name in subfolders:
            # 🔍 kiểm tra đã tồn tại trên Drive chưa
            query_sub = (
                f"name='{name}' and "
                f"mimeType='application/vnd.google-apps.folder' and "
                f"'{root_folder_id}' in parents and trashed=false"
            )
            check_sub = requests.get(
                f"{drive_api_url}?q={requests.utils.quote(query_sub)}&fields=files(id,name)",
                headers=headers
            )

            files = check_sub.json().get("files", []) if check_sub.status_code == 200 else []
            if files:
                sub_id = files[0]["id"]

            else:
                # 🆕 tạo mới thư mục con
                create_sub = requests.post(
                    drive_api_url,
                    headers=headers,
                    json={
                        "name": name,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [root_folder_id]
                    }
                )
                if create_sub.status_code not in [200, 201]:

                    continue
                sub_id = create_sub.json()["id"]


            # 💾 Lưu vào bảng DriveFolder
            DriveFolder.objects.update_or_create(
                drive=user_drive,
                name=name,
                defaults={
                    "folder_id": sub_id,
                    "parent_folder": None,
                }
            )

            created_folders.append({
                "name": name,
                "folder_id": sub_id
            })

        # =============================
        # 6️⃣ Phản hồi kết quả
        # =============================
        # Chuyển list → dict
        folders_dict = {item["name"]: item["folder_id"] for item in created_folders}

        return JsonResponse({
            "message": "Tạo đầy đủ thư mục thành công",
            "root_folder_id": root_folder_id,
            "user_email": email,
            "subfolders": created_folders
        }, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# API tạo Folder, file sheet
@csrf_exempt
def create_folder_sheet_view(request):

    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        access_token = data.get("access_token")

        if not access_token:
            return JsonResponse({"error": "Missing access_token"}, status=400)

        # =============================
        # 1️⃣ Verify Google User
        # =============================
        verify = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if verify.status_code != 200:
            return JsonResponse({"error": "Invalid access_token"}, status=400)

        user_info = verify.json()
        email = user_info.get("email")

        # =============================
        # 2️⃣ Get / Create User
        # =============================
        user, created = User.objects.get_or_create(email=email)

        drive_api = "https://www.googleapis.com/drive/v3/files"
        sheets_api = "https://sheets.googleapis.com/v4/spreadsheets"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # =============================
        # 3️⃣ Ensure Folder: chung_tu_ho_kinh_doanh
        # =============================
        FOLDER_NAME = "chung_tu_ho_kinh_doanh"

        query = (
            f"name='{FOLDER_NAME}' and "
            "mimeType='application/vnd.google-apps.folder' and "
            "'root' in parents and trashed=false"
        )

        search = requests.get(
            f"{drive_api}?q={requests.utils.quote(query)}&fields=files(id,name)",
            headers=headers,
        )

        if search.status_code == 200 and search.json().get("files"):
            root_folder_id = search.json()["files"][0]["id"]

        else:
            create_folder = requests.post(
                drive_api,
                headers=headers,
                json={
                    "name": FOLDER_NAME,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": ["root"],
                },
            )
            if create_folder.status_code not in (200, 201):
                return JsonResponse(
                    {"error": "Create folder failed", "detail": create_folder.text},
                    status=400,
                )

            root_folder_id = create_folder.json()["id"]


        # =============================
        # 4️⃣ Lưu vào UserDrive  ✅ (GIỐNG API CŨ)
        # =============================
        user_drive, _ = UserDrive.objects.update_or_create(
            user=user,
            defaults={
                "drive_folder_id": root_folder_id,
                "access_token": access_token,
                "token_expiry": timezone.now() + timezone.timedelta(hours=1)
            }
        )

        # =============================
        # 5️⃣ Ensure Sheet: so_thu_chi_hkd
        # =============================
        SHEET_NAME = "so_thu_chi_hkd"

        query_sheet = (
            f"name='{SHEET_NAME}' and "
            f"mimeType='application/vnd.google-apps.spreadsheet' and "
            f"'{root_folder_id}' in parents and trashed=false"
        )

        search_sheet = requests.get(
            f"{drive_api}?q={requests.utils.quote(query_sheet)}&fields=files(id,name)",
            headers=headers,
        )

        if search_sheet.status_code == 200 and search_sheet.json().get("files"):
            spreadsheet_id = search_sheet.json()["files"][0]["id"]


        else:
            create_sheet = requests.post(
                drive_api,
                headers=headers,
                json={
                    "name": SHEET_NAME,
                    "mimeType": "application/vnd.google-apps.spreadsheet",
                    "parents": [root_folder_id],
                },
            )

            if create_sheet.status_code not in (200, 201):
                return JsonResponse(
                    {"error": "Create sheet failed", "detail": create_sheet.text},
                    status=400,
                )

            spreadsheet_id = create_sheet.json()["id"]

            # Thêm tab Thu / Chi
            requests.post(
                f"{sheets_api}/{spreadsheet_id}:batchUpdate",
                headers=headers,
                json={
                    "requests": [
                        {"addSheet": {"properties": {"title": "so_doanh_thu"}}},
                        {"addSheet": {"properties": {"title": "so_chi_phi"}}},
                    ]
                },
            )

        # =============================
        # 6️⃣ Lưu vào DriveFolder  ✅
        # =============================
        DriveFolder.objects.update_or_create(
            drive=user_drive,
            name=SHEET_NAME,
            defaults={
                "folder_id": spreadsheet_id,   # vẫn lưu id Drive
                "parent_folder": None,
            },
        )

        creds = Credentials(
            token=access_token,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )

        # =============================
        # 7️⃣ Response
        # =============================
        return JsonResponse(
            {
                "message": "Tạo folder + sheet HKD thành công",
                "user_email": email,
                "root_folder_id": root_folder_id,
                "sheet": {
                    "name": SHEET_NAME,
                    "spreadsheet_id": spreadsheet_id,
                },
            },
            status=200,
        )

    except Exception as e:

        return JsonResponse({"error": str(e)}, status=500)

