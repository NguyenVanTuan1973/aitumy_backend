from celery import shared_task
from .models import DocumentMetadata
from .extract_utils import extract_and_parse
from django.core.files.storage import default_storage

from drive_integration.services.document_sync_service import sync_document_to_google

from drive_integration.services.google_drive_upload_service import upload_file_to_drive


@shared_task(bind=True, max_retries=3)
def process_document_task(self, doc_id, stored_path):
    """
    Background task to extract data and upload to Drive.
`   stored_path` is the path in Django storage (relative or absolute depending on your storage).
    """
    try:
        doc = DocumentMetadata.objects.get(id=doc_id)
        # local_path resolution
        try:
            local_path = default_storage.path(stored_path)
        except Exception:
            # if using remote storage, you may need to download to temp
            local_path = stored_path


        result = extract_and_parse(local_path)
        fields = result.get('fields', {})
        for k, v in fields.items():
            if hasattr(doc, k):
                setattr(doc, k, v)
        doc.ocr_text = result.get('ocr_text')
        doc.extract_log = result.get('log')
        doc.status = 'enable'
        doc.save()

        drive_resp = upload_file_to_drive(local_path, doc, doc.user)
        if drive_resp:
            doc.drive_file_id = drive_resp.get('file_id')
            doc.drive_link = drive_resp.get('webViewLink')
            doc.drive_path = drive_resp.get('path')
            doc.drive_mime = drive_resp.get('mime')
            doc.save()
        return {'status': 'ok'}
    except Exception as exc:
        try:
            self.retry(exc=exc, countdown=10)
        except Exception:
            # final fail
            DocumentMetadata.objects.filter(id=doc_id).update(status='invalid')
            return {'status': 'failed', 'error': str(exc)}

def retry_failed_documents():
    failed_docs = DocumentMetadata.objects.filter(
        sync_status=DocumentMetadata.SYNC_FAILED
    )

    for doc in failed_docs:
        try:
            sync_document_to_google(
                user=doc.user,
                document=doc,
                file_path=doc.file.path
            )
        except Exception:
            continue
