from typing import List, Dict

from .google_sheet_get_data_service import GoogleSheetGetDataService


class BaseSheetService:
    """
    Base service cho tất cả các SheetServiceShow

    Chỉ có nhiệm vụ:
    - đọc dữ liệu từ Google Sheet
    - convert rows → dict theo header
    """

    SHEET_RANGE = "data_source!A1:AA"  # 27 columns

    def __init__(self, *, user, params, spreadsheet_id: str):
        self.user = user
        self.params = params
        self.spreadsheet_id = spreadsheet_id

        self.sheet_reader = GoogleSheetGetDataService(
            user=user,
            spreadsheet_id=spreadsheet_id,
        )

    # =====================================================
    # LOAD DATA_SOURCE
    # =====================================================

    def load_sheet_rows(self, sheet_name="data_source") -> List[Dict]:
        sheet_range = f"{sheet_name}!A1:AZ"

        try:
            result = (
                self.sheet_reader.sheets
                .spreadsheets()
                .values()
                .get(
                    spreadsheetId=self.spreadsheet_id,
                    range=sheet_range,
                )
                .execute()
            )
        except Exception:
            return []

        rows = result.get("values", [])

        if not rows:
            return []

        headers = rows[0]
        data_rows = rows[1:]

        records = []

        for r in data_rows:

            if not r:
                continue

            record = {}

            for i, header in enumerate(headers):
                record[header] = r[i] if i < len(r) else None

            records.append(record)

        return records
