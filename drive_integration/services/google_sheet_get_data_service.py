from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .google_oauth_service import GoogleOAuthService

class GoogleSheetGetDataService:

    def __init__(self, *, user, spreadsheet_id: str):
        self.user = user
        self.spreadsheet_id = spreadsheet_id

        creds = GoogleOAuthService.get_credentials_for_user(user=user)
        if not creds:
            raise Exception("USER_NOT_CONNECTED_GOOGLE")

        self.sheets = build("sheets", "v4", credentials=creds)

    # =====================================================
    # READ OVERVIEW (TOÀN BỘ DỮ LIỆU TRONG NĂM)
    # =====================================================
    def read_overview(self):

        all_rows = []

        for sheet_name in ["so_doanh_thu", "so_chi_phi"]:
            try:
                result = self.sheets.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{sheet_name}!A:E",
                ).execute()
            except HttpError:
                continue

            rows = result.get("values", [])
            for r in rows:
                if not r:
                    continue

                all_rows.append({
                    "sheet_name": sheet_name,  # 👈 NGUỒN DỮ LIỆU
                    "row": r,
                })

        return all_rows

    # =====================================================
    # READ BY PERIOD (OPTIONAL – DÙNG SAU)
    # =====================================================
    def read_by_period(self, *, start_date, end_date):

        filtered_rows = []

        for sheet_name in ["so_doanh_thu", "so_chi_phi"]:
            try:
                result = self.sheets.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{sheet_name}!A:E",
                ).execute()
            except HttpError:
                continue

            rows = result.get("values", [])
            for r in rows:
                if not r or len(r) < 1:
                    continue

                try:
                    row_date = datetime.strptime(r[0], "%Y-%m-%d").date()
                except Exception:
                    continue

                if start_date <= row_date <= end_date:
                    # filtered_rows.append(r)
                    filtered_rows.append({
                        "sheet_name": sheet_name,
                        "row": r,
                    })

        return filtered_rows
