from rest_framework import serializers
from .models import WebContent, FAQItem, FAQCategory
from knowledge_base.models import LegalClause


class WebContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebContent
        fields = ["content_key", "title", "content", "updated_at"]

class LegalClauseSerializer(serializers.ModelSerializer):
    display = serializers.SerializerMethodField()
    document = serializers.CharField(source="document.code")

    class Meta:
        model = LegalClause
        fields = ["id", "display", "document"]

    def get_display(self, obj):
        return obj.display_ref()

class FAQItemSerializer(serializers.ModelSerializer):
    legal_clauses = LegalClauseSerializer(many=True)

    class Meta:
        model = FAQItem
        fields = ["id", "question", "answer", "legal_clauses"]

class FAQCategorySerializer(serializers.ModelSerializer):
    faqs = FAQItemSerializer(many=True)

    class Meta:
        model = FAQCategory
        fields = ["id", "name", "faqs"]