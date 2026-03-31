from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from users.models import UserDrive

from .google_drive_service import get_user_credentials


def upload_file_to_drive(file_path, doc_obj, user):
    """
    Upload file lên Google Drive của user
    Return dict: file_id, webViewLink, mimeType
    """

    creds = get_user_credentials(user)
    if not creds:
        raise Exception("User not connected Google Drive")

    user_drive = UserDrive.objects.filter(user=user).first()
    if not user_drive or not user_drive.drive_folder_id:
        raise Exception("Drive folder not initialized")

    service = build("drive", "v3", credentials=creds)

    # 📂 Xác định folder theo loại chứng từ
    parent_folder_id = _get_or_create_subfolder(
        service,
        user_drive.drive_folder_id,
        doc_obj.doc_type or "khac"
    )

    file_metadata = {
        "name": doc_obj.file_name,
        "parents": [parent_folder_id],
    }

    media = MediaFileUpload(
        file_path,
        resumable=True
    )

    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink, mimeType"
        ).execute()

        return {
            "file_id": file.get("id"),
            "webViewLink": file.get("webViewLink"),
            "mimeType": file.get("mimeType"),
        }

    except HttpError as e:
        raise Exception(f"Google Drive upload failed: {e}")


# ===============================
# INTERNAL HELPER
# ===============================

def _get_or_create_subfolder(service, parent_id, name):
    """
    Mỗi loại chứng từ = 1 subfolder
    """

    query = (
        f"name='{name}' and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"'{parent_id}' in parents and trashed=false"
    )

    resp = service.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()

    files = resp.get("files", [])
    if files:
        return files[0]["id"]

    folder_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }

    folder = service.files().create(
        body=folder_metadata,
        fields="id"
    ).execute()

    return folder.get("id")
