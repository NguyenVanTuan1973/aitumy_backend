import requests

DRIVE_API = "https://www.googleapis.com/drive/v3/files"
SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"


class GoogleDriveClient:

    def __init__(self, access_token):
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    # ======================================================
    # SEARCH
    # ======================================================

    def search(self, query):
        res = requests.get(
            f"{DRIVE_API}?q={requests.utils.quote(query)}&fields=files(id,name)",
            headers=self.headers,
        )
        if res.status_code == 200:
            return res.json().get("files", [])
        raise Exception(res.text)

    # ======================================================
    # CREATE FOLDER
    # ======================================================

    def create_folder(self, name, parent_id=None):

        body = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_id:
            body["parents"] = [parent_id]

        res = requests.post(DRIVE_API, headers=self.headers, json=body)

        if res.status_code not in (200, 201):
            raise Exception(res.text)

        return res.json()["id"]

    # ======================================================
    # CREATE SHEET
    # ======================================================

    def create_sheet(self, name, parent_id=None):

        body = {
            "name": name,
            "mimeType": "application/vnd.google-apps.spreadsheet",
        }

        if parent_id:
            body["parents"] = [parent_id]

        res = requests.post(DRIVE_API, headers=self.headers, json=body)

        if res.status_code not in (200, 201):
            raise Exception(res.text)

        return res.json()["id"]

    # ======================================================
    # ADD MULTIPLE SHEETS (TABS)
    # ======================================================

    def add_sheets(self, spreadsheet_id, sheet_names):

        url = f"{SHEETS_API}/{spreadsheet_id}:batchUpdate"

        requests_body = [
            {"addSheet": {"properties": {"title": name}}}
            for name in sheet_names
        ]

        res = requests.post(
            url,
            headers=self.headers,
            json={"requests": requests_body},
        )

        if res.status_code not in (200, 201):
            raise Exception(res.text)

    # ======================================================
    # WRITE HEADER / ROW
    # ======================================================

    def write_row(self, spreadsheet_id, sheet_name, values):

        url = f"{SHEETS_API}/{spreadsheet_id}/values/{sheet_name}!A1:append"

        res = requests.post(
            url,
            headers=self.headers,
            params={"valueInputOption": "RAW"},
            json={"values": [values]},
        )

        if res.status_code not in (200, 201):
            raise Exception(res.text)

    # ======================================================
    # GET SHEET DATA
    # ======================================================

    def get_values(self, spreadsheet_id, sheet_name):

        url = f"{SHEETS_API}/{spreadsheet_id}/values/{sheet_name}"

        res = requests.get(url, headers=self.headers)

        if res.status_code != 200:
            raise Exception(res.text)

        return res.json().get("values", [])

    # ======================================================
    # OPTIONAL: DELETE SHEET TAB
    # ======================================================

    def delete_sheet(self, spreadsheet_id, sheet_id):

        url = f"{SHEETS_API}/{spreadsheet_id}:batchUpdate"

        res = requests.post(
            url,
            headers=self.headers,
            json={
                "requests": [
                    {
                        "deleteSheet": {
                            "sheetId": sheet_id
                        }
                    }
                ]
            },
        )

        if res.status_code not in (200, 201):
            raise Exception(res.text)