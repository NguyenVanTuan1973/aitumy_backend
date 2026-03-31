from rest_framework import serializers
from .models import DocumentMetadata, DocumentGroup, GroupDocument


class DocumentMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentMetadata
        fields = '__all__'
        read_only_fields = ("user", "upload_date", "drive_file_id", "drive_link", "ocr_text", "extract_log")


class DocumentUploadSerializer(serializers.Serializer):
    files = serializers.ListField(child=serializers.FileField(), allow_empty=False)


class GroupDocumentSimpleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=[("main", "Chính"), ("support", "Bổ trợ")], default="support")


class DocumentGroupCreateSerializer(serializers.Serializer):
    group_code = serializers.CharField(required=False, allow_blank=True)
    group_name = serializers.CharField()
    group_type = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    documents = GroupDocumentSimpleSerializer(many=True, required=False)


class DocumentGroupSerializer(serializers.ModelSerializer):
    documents = serializers.SerializerMethodField()

    class Meta:
        model = DocumentGroup
        fields = '__all__'

    def get_documents(self, obj):
        return [{
            'id': gd.document.id,
            'file_name': gd.document.file_name,
            'role': gd.role
        } for gd in obj.group_documents.select_related('document').all()]