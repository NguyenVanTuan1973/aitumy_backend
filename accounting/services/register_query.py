import gspread
from google.oauth2.credentials import Credentials
from django.conf import settings

from ..utils.period_range import build_period_range
from datetime import datetime, timedelta


def get_gspread_client(user):

    drive = user.drive

    creds = Credentials(
        token=drive.access_token,
        refresh_token=drive.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )

    return gspread.authorize(creds)


def excel_date_to_date(serial):
    return (datetime(1899, 12, 30) + timedelta(days=float(serial))).date()


def query_sheet_data(
        user,
        sheet_id,
        doc_register,
        period_type,
        year,
        month=None,
        quarter=None
):

    # gc = get_gspread_client(user.drive.access_token)
    gc = get_gspread_client(user)

    spreadsheet = gc.open_by_key(sheet_id)

    worksheet = spreadsheet.worksheet("data_source")

    rows = worksheet.get_all_records()

    start_date, end_date = build_period_range(
        period_type,
        year,
        month,
        quarter
    )

    results = []

    for r in rows:

        register = str(r.get("doc_register", "")).strip().upper()
        target = str(doc_register).strip().upper()

        if register != target:
            continue

        doc_date_raw = r.get("doc_date")

        if not doc_date_raw:
            continue

        doc_date = parse_sheet_date(doc_date_raw)

        if not doc_date:
            continue

        if start_date <= doc_date <= end_date:
            results.append(r)

    return results

def parse_sheet_date(value):

    if value is None or value == "":
        return None

    # ======================
    # 1️⃣ Excel serial number
    # ======================

    if isinstance(value, (int, float)):
        return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()

    # ======================
    # 2️⃣ ISO datetime string
    # ======================

    if isinstance(value, str):

        try:
            return datetime.fromisoformat(value.replace("Z", "")).date()
        except Exception:
            pass

        # ======================
        # 3️⃣ YYYY-MM-DD
        # ======================

        try:
            return datetime.strptime(value.split("T")[0], "%Y-%m-%d").date()
        except Exception:
            pass

    return None