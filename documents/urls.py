from django.urls import path
from .views import (DocumentUploadAPIView, DocumentListAPIView, CreateGroupAPIView, DocumentDetailAPIView,
                    DocumentRecognizeAPIView, DocumentSaveAPIView, ExportFilePdfView)


urlpatterns = [
    path('upload/', DocumentUploadAPIView.as_view(), name='doc-upload'),
    path('', DocumentListAPIView.as_view(), name='doc-list'),
    path('groups/', CreateGroupAPIView.as_view(), name='group-create'),
    path('<int:pk>/', DocumentDetailAPIView.as_view(), name='doc-detail'),
    path('recognize/', DocumentRecognizeAPIView.as_view(), name='recognize'),
    path('save/', DocumentSaveAPIView.as_view(), name='save'),
    path('export-pdf/', ExportFilePdfView.as_view(), name='export-pdf')
]