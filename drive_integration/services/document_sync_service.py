from .google_drive_upload_service import upload_file_to_drive
from users.models import DriveFolder

from .google_sheet_append_service import GoogleSheetAppendService


def sync_document_to_google(user, document, file_path):
    """
    Orchestrate:
    - Upload Drive
    - Append Sheet
    - Rollback nếu lỗi
    """

    try:
        # 1️⃣ Upload file → Drive
        drive_result = upload_file_to_drive(
            file_path=file_path,
            doc_obj=document,
            user=user
        )

        if not drive_result:
            raise Exception("Upload Drive failed")

        document.drive_file_id = drive_result["file_id"]
        document.drive_file_url = drive_result.get("webViewLink")
        document.save(update_fields=[
            "drive_file_id",
            "drive_file_url"
        ])

        # 2️⃣ Append → Sheet

        sheet_node = DriveFolder.objects.filter(
            drive=user.drive,
            node_type="sheet"
        ).first()

        if not sheet_node:
            raise Exception("Spreadsheet not initialized")

        spreadsheet_id = sheet_node.sheet_id

        values = [[
            document.doc_number,
            document.doc_date.strftime("%Y-%m-%d"),
            document.amount,
            document.doc_type,
        ]]

        GoogleSheetAppendService.append(
            user=user,
            spreadsheet_id=spreadsheet_id,
            range_name="documents_metadata!A1",
            values=values
        )

        # 3️⃣ Thành công
        document.sync_status = document.SYNC_SUCCESS
        document.sync_error = None
        document.save(update_fields=[
            "sync_status",
            "sync_error"
        ])

    except Exception as e:
        # ❌ FAILED → rollback logic
        document.sync_status = document.SYNC_FAILED
        document.sync_error = str(e)
        document.save(update_fields=[
            "sync_status",
            "sync_error"
        ])

        # 🚨 KHÔNG xoá file Drive ngay (audit)
        raise
