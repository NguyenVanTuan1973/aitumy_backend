import requests
from users.models import UserDrive


class GoogleSheetAppendService:
    @staticmethod
    def append(
        *,
        user,
        spreadsheet_id: str,
        range_name: str,
        values: list,
    ):
        """
        Append data to Google Sheet using USER OAuth token
        """

        # =====================================================
        # 1️⃣ GET USER TOKEN
        # =====================================================
        user_drive = UserDrive.objects.filter(user=user).first()

        if not user_drive or not user_drive.access_token:
            raise Exception("User has not connected Google")

        access_token = user_drive.access_token

        # =====================================================
        # 2️⃣ CALL GOOGLE SHEETS API
        # =====================================================
        url = (
            f"https://sheets.googleapis.com/v4/spreadsheets/"
            f"{spreadsheet_id}/values/{range_name}:append"
            "?valueInputOption=USER_ENTERED"
            "&insertDataOption=INSERT_ROWS"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "values": values
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code not in (200, 201):
            raise Exception(
                f"Sheets append failed: {response.status_code} - {response.text}"
            )

        return response.json()
