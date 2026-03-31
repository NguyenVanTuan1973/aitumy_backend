from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from drive_integration.services.google_drive_service import get_user_credentials


class SheetReaderService:

    @staticmethod
    def _get_sheets_service(user):
        creds = get_user_credentials(user)
        if not creds:
            raise ValueError("User chưa kết nối Google Drive")

        return build("sheets", "v4", credentials=creds)

    @staticmethod
    def _find_spreadsheet_id_by_name(user, file_name: str):
        """
        Tìm spreadsheet theo tên file
        """

        creds = get_user_credentials(user)
        if not creds:
            raise ValueError("User chưa kết nối Google Drive")

        drive_service = build("drive", "v3", credentials=creds)

        query = (
            f"name = '{file_name}' "
            "and mimeType = 'application/vnd.google-apps.spreadsheet' "
            "and trashed = false"
        )

        results = drive_service.files().list(
            q=query,
            fields="files(id, name)",
            spaces="drive",
        ).execute()

        files = results.get("files", [])

        if not files:
            raise ValueError(f"Không tìm thấy file Google Sheet: {file_name}")

        return files[0]["id"]

    @staticmethod
    def read_sheet(request, file_name: str, sheet_name: str):
        """
        Đọc toàn bộ dữ liệu từ sheet và convert thành list[dict]
        """

        user = request.user

        spreadsheet_id = SheetReaderService._find_spreadsheet_id_by_name(
            user=user,
            file_name=file_name,
        )

        sheets_service = SheetReaderService._get_sheets_service(user)

        try:
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=sheet_name,
            ).execute()
        except HttpError as e:
            raise ValueError(f"Lỗi đọc sheet: {str(e)}")

        values = result.get("values", [])

        if not values:
            return []

        # ===== Dòng đầu là header =====
        headers = values[0]
        rows = values[1:]

        data = []

        for row in rows:
            row_dict = {}

            for idx, header in enumerate(headers):
                value = row[idx] if idx < len(row) else ""
                row_dict[header] = value

            # Bỏ dòng trống hoàn toàn
            if any(str(v).strip() for v in row_dict.values()):
                data.append(row_dict)

        return data