from datetime import datetime
from django.conf import settings
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from users.models import UserDrive


# =========================================================
# 🔐 AUTH
# =========================================================

def get_user_credentials(user):
    drive = UserDrive.objects.filter(user=user).first()

    if not drive or not drive.access_token:
        return None

    # code mới chưa test
    creds = Credentials(
        token=drive.access_token,
        refresh_token=drive.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=[
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/spreadsheets"
        ],
    )

    # 🔥 Auto refresh nếu hết hạn
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

        drive.access_token = creds.token
        drive.token_expiry = creds.expiry
        drive.save(update_fields=["access_token", "token_expiry", "updated_at"])

    return creds


def get_drive_service(user):
    creds = get_user_credentials(user)
    if not creds:
        raise Exception("User has not connected Google Drive")
    return build("drive", "v3", credentials=creds)


def get_sheets_service(user):
    creds = get_user_credentials(user)
    if not creds:
        raise Exception("User has not connected Google Sheets")
    return build("sheets", "v4", credentials=creds)


# =========================================================
# 📁 FOLDER
# =========================================================

def ensure_folder(service, parent_folder_id, name):
    query = (
        f"name = '{name}' "
        "and mimeType = 'application/vnd.google-apps.folder' "
        "and trashed = false "
    )

    if parent_folder_id:
        query += f"and '{parent_folder_id}' in parents"

    resp = service.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()

    items = resp.get("files", [])

    if items:
        return items[0]["id"]

    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }

    if parent_folder_id:
        file_metadata["parents"] = [parent_folder_id]

    folder = service.files().create(
        body=file_metadata,
        fields="id"
    ).execute()

    return folder.get("id")


# =========================================================
# 📊 GOOGLE SHEET
# =========================================================

def create_spreadsheet(user, title, parent_folder_id):
    sheets_service = get_sheets_service(user)

    spreadsheet = sheets_service.spreadsheets().create(
        body={
            "properties": {"title": title}
        }
    ).execute()

    spreadsheet_id = spreadsheet["spreadsheetId"]

    # Move sheet vào đúng folder năm
    drive_service = get_drive_service(user)

    drive_service.files().update(
        fileId=spreadsheet_id,
        addParents=parent_folder_id,
        removeParents="root",
        fields="id, parents"
    ).execute()

    return spreadsheet_id


def create_sheet_tab(user, spreadsheet_id, sheet_name):
    sheets_service = get_sheets_service(user)

    body = {
        "requests": [{
            "addSheet": {
                "properties": {
                    "title": sheet_name
                }
            }
        }]
    }

    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body
    ).execute()


# =========================================================
# 🚀 INIT STRUCTURE
# =========================================================

def init_tumy_structure(user, organization):
    drive_service = get_drive_service(user)

    current_year = datetime.now().year

    # 1️⃣ TuMy_Accounting
    root_folder_id = ensure_folder(
        drive_service,
        None,
        "TuMy_Accounting"
    )

    # 2️⃣ Folder năm
    year_folder_id = ensure_folder(
        drive_service,
        root_folder_id,
        str(current_year)
    )

    # 3️⃣ Sheet HKD_DATA
    sheet_title = f"HKD_DATA_{current_year}"

    spreadsheet_id = create_spreadsheet(
        user,
        sheet_title,
        year_folder_id
    )

    # 4️⃣ Tạo các tab
    create_sheet_tab(user, spreadsheet_id, "opening_balances")
    create_sheet_tab(user, spreadsheet_id, "documents_metadata")
    create_sheet_tab(user, spreadsheet_id, "data_source")

    if organization.plan_type == "hkd_pro":
        create_sheet_tab(user, spreadsheet_id, "inventory_opening")

    # 5️⃣ CHUNG_TU
    chung_tu_folder_id = ensure_folder(
        drive_service,
        year_folder_id,
        "CHUNG_TU"
    )

    for month in range(1, 13):
        ensure_folder(
            drive_service,
            chung_tu_folder_id,
            f"{month:02d}"
        )

    return {
        "year": current_year,
        "root_folder_id": root_folder_id,
        "year_folder_id": year_folder_id,
        "spreadsheet_id": spreadsheet_id,
        "chung_tu_folder_id": chung_tu_folder_id,
    }