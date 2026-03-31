from rest_framework import serializers
from .models import WebContent


class WebContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebContent
        fields = ["content_key", "title", "content", "updated_at"]