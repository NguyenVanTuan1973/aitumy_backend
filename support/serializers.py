from rest_framework import serializers
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id",
            "sender_type",
            "content",
            "is_read",
            "created_at",
        ]

class ConversationListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "status",
            "created_at",
            "last_message",
            "unread_count",
        ]

    def get_last_message(self, obj):
        message = obj.messages.order_by("-created_at").first()
        if not message:
            return None
        return {
            "content": message.content,
            "sender_type": message.sender_type,
            "created_at": message.created_at,
        }

    def get_unread_count(self, obj):
        return obj.messages.filter(
            sender_type="admin",
            is_read=False
        ).count()
