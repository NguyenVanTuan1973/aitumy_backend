from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.urls import reverse
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from aitumy_backend.documents.models import DocumentMetadata

User = get_user_model()

class DocumentsAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass')
        self.client = APIClient()
        self.client.force_authenticate(self.user)


    def test_upload_document(self):
        url = reverse('doc-upload')
        content = b'%PDF-1.4 fake pdf content'
        f = SimpleUploadedFile('test.pdf', content, content_type='application/pdf')
        resp = self.client.post(url, {'files': [f]}, format='multipart')
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn('created', data)
        self.assertEqual(len(data['created']), 1)


    def test_create_group(self):
        # create a document first
        doc = DocumentMetadata.objects.create(user=self.user, original_filename='a.pdf', file_name='a.pdf', file_format='pdf')
        url = reverse('group-create')
        payload = {
            'group_name': 'Test Group',
            'documents': [{'id': doc.id, 'role': 'main'}]
        }
        resp = self.client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data['group_name'], 'Test Group')