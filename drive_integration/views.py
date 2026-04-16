import io
import requests

import datetime

from django.conf import settings
from django.utils import timezone
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseUpload
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from users.utils.google_oauth import exchange_code_for_tokens
from users.models import User, UserDrive, DriveFolder, UserSession, OrganizationMember
import uuid
from documents.extract_utils import extract_from_pdf
from documents.models import DocumentMetadata, RegisterMapping

from .serializers import CreateDocumentSerializer
from .services.drive_status_service import DriveStatusService
from .services.drive_workspace_service import DriveWorkspaceService
from .services.get_sheet_data_router import get_sheet_data_by_user, get_user_plan_code
from .services.google_oauth_service import GoogleOAuthService

from googleapiclient.discovery import build
from .utils.period_utils import get_period_range
from .utils.resolve_doc_register import resolve_doc_register



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
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
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
        import json
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
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
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
        membership = (
            OrganizationMember.objects
            .select_related("organization__subscription__plan")
            .filter(user=request.user, is_active=True)
            .first()
        )

        plan_code = None

        if membership and membership.organization.subscription:
            plan_code = membership.organization.subscription.plan.code

        normalized_values = []

        for row in values:

            row_dict = {}

            if isinstance(row, list):

                for idx, col in enumerate(self.DATA_SOURCE_COLUMNS):
                    row_dict[col] = row[idx] if idx < len(row) else 0

            else:

                for col in self.DATA_SOURCE_COLUMNS:
                    row_dict[col] = row.get(col, 0)

            # ============================================
            # 🔥 MAP DOC REGISTER TẠI ĐÂY
            # ============================================
            job_code = row_dict.get("job_code")

            doc_register = resolve_doc_register(
                plan_code=plan_code,
                job_code=job_code
            )

            row_dict["doc_register"] = doc_register

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

        import json

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

