# from datetime import datetime
# import requests
# from django.utils import timezone
#
# from users.models import UserDrive, DriveFolder
#
#
# FREE_FOLDER_NAME = "chung_tu_ho_kinh_doanh"
# FREE_SHEET_PREFIX = "so_thu_chi_hkd"
#
#
# class GoogleSheetUserFreeService:
#     """
#     Service tạo & quản lý Folder + Google Sheet cho USER FREE
#     (HÀNH VI GIỐNG API CŨ – ỔN ĐỊNH VỚI drive.file)
#     """
#
#     DRIVE_API = "https://www.googleapis.com/drive/v3/files"
#     SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
#
#     def __init__(self, *, user, drive: UserDrive):
#         self.user = user
#         self.drive = drive
#         self.access_token = drive.access_token
#
#         self.headers = {
#             "Authorization": f"Bearer {self.access_token}",
#             "Content-Type": "application/json",
#         }
#
#     # =====================================================
#     # PUBLIC
#     # =====================================================
#
#     def ensure_workspace(self) -> dict:
#         """
#         Entry point cho DriveWorkspaceService (FREE)
#         """
#         root_folder_id = self._ensure_root_folder()
#         spreadsheet_id = self._ensure_sheet(root_folder_id)
#
#         return {
#             "folder_id": root_folder_id,
#             "spreadsheet_id": spreadsheet_id,
#         }
#
#     # =====================================================
#     # INTERNAL
#     # =====================================================
#
#     def _ensure_root_folder(self) -> str:
#         """
#         Ensure folder: chung_tu_ho_kinh_doanh (root)
#         """
#         query = (
#             f"name='{FREE_FOLDER_NAME}' and "
#             "mimeType='application/vnd.google-apps.folder' and "
#             "'root' in parents and trashed=false"
#         )
#
#         res = requests.get(
#             f"{self.DRIVE_API}?q={requests.utils.quote(query)}&fields=files(id,name)",
#             headers=self.headers,
#         )
#         res.raise_for_status()
#
#         files = res.json().get("files", [])
#         if files:
#             folder_id = files[0]["id"]
#         else:
#             create = requests.post(
#                 self.DRIVE_API,
#                 headers=self.headers,
#                 json={
#                     "name": FREE_FOLDER_NAME,
#                     "mimeType": "application/vnd.google-apps.folder",
#                     "parents": ["root"],
#                 },
#             )
#             create.raise_for_status()
#             folder_id = create.json()["id"]
#
#         # ✅ Update UserDrive (GIỐNG API CŨ)
#         if self.drive.drive_folder_id != folder_id:
#             self.drive.drive_folder_id = folder_id
#             self.drive.token_expiry = timezone.now() + timezone.timedelta(hours=1)
#             self.drive.save(update_fields=["drive_folder_id", "token_expiry"])
#
#         DriveFolder.objects.update_or_create(
#             drive=self.drive,
#             folder_id=folder_id,
#             defaults={
#                 "name": FREE_FOLDER_NAME,
#                 "node_type": "folder",
#                 "parent_folder": None,
#             },
#         )
#
#         return folder_id
#
#     # -----------------------------------------------------
#
#     def _ensure_sheet(self, root_folder_id: str) -> str:
#         """
#         Ensure sheet: so_thu_chi_hkd_YYYY (NẰM TRONG FOLDER)
#         """
#         year = datetime.now().year
#         sheet_name = f"{FREE_SHEET_PREFIX}_{year}"
#
#         # 1️⃣ Search sheet trong folder
#         query = (
#             f"name='{sheet_name}' and "
#             "mimeType='application/vnd.google-apps.spreadsheet' and "
#             f"'{root_folder_id}' in parents and trashed=false"
#         )
#
#         res = requests.get(
#             f"{self.DRIVE_API}?q={requests.utils.quote(query)}&fields=files(id,name)",
#             headers=self.headers,
#         )
#         res.raise_for_status()
#
#         files = res.json().get("files", [])
#         if files:
#             spreadsheet_id = files[0]["id"]
#         else:
#             # 2️⃣ TẠO SHEET (KHÔNG TRUST parents)
#             create = requests.post(
#                 self.DRIVE_API,
#                 headers=self.headers,
#                 json={
#                     "name": sheet_name,
#                     "mimeType": "application/vnd.google-apps.spreadsheet",
#                 },
#             )
#             create.raise_for_status()
#             spreadsheet_id = create.json()["id"]
#
#             # 🔥 3️⃣ FORCE MOVE VÀO FOLDER (QUAN TRỌNG)
#             self._force_move_into_folder(spreadsheet_id, root_folder_id)
#
#             # 4️⃣ Add tabs Thu / Chi
#             requests.post(
#                 f"{self.SHEETS_API}/{spreadsheet_id}:batchUpdate",
#                 headers=self.headers,
#                 json={
#                     "requests": [
#                         {"addSheet": {"properties": {"title": "so_doanh_thu"}}},
#                         {"addSheet": {"properties": {"title": "so_chi_phi"}}},
#                     ]
#                 },
#             ).raise_for_status()
#
#         # 5️⃣ Lưu DB (DriveFolder)
#         root_folder = DriveFolder.objects.filter(
#             drive=self.drive,
#             folder_id=root_folder_id
#         ).first()
#
#         DriveFolder.objects.update_or_create(
#             drive=self.drive,
#             folder_id=spreadsheet_id,
#             defaults={
#                 "name": sheet_name,
#                 "node_type": "sheet",
#                 "parent_folder": root_folder,
#             },
#         )
#
#         # DriveFolder.objects.update_or_create(
#         #     drive=self.drive,
#         #     name=sheet_name,
#         #     defaults={
#         #         "folder_id": spreadsheet_id,
#         #         "parent_folder": None,
#         #     },
#         # )
#
#         return spreadsheet_id
#
#     # -----------------------------------------------------
#
#     def _force_move_into_folder(self, file_id: str, folder_id: str):
#         """
#         ÉP file nằm trong folder (FIX drive.file behavior)
#         """
#         meta = requests.get(
#             f"{self.DRIVE_API}/{file_id}?fields=parents",
#             headers=self.headers,
#         )
#         meta.raise_for_status()
#
#         parents = meta.json().get("parents", [])
#         if folder_id in parents:
#             return
#
#         remove_parents = ",".join(parents)
#
#         requests.patch(
#             f"{self.DRIVE_API}/{file_id}"
#             f"?addParents={folder_id}&removeParents={remove_parents}",
#             headers=self.headers,
#         ).raise_for_status()
#
