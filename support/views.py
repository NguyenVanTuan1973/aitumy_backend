from datetime import timezone, timedelta

from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Conversation, Message
from .serializers import (
    ConversationListSerializer,
    MessageSerializer
)

class UserConversationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = Conversation.objects.filter(
            user=request.user
        ).order_by("-created_at")

        serializer = ConversationListSerializer(
            conversations,
            many=True
        )

        return Response(serializer.data)

class UserConversationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        conversation = get_object_or_404(
            Conversation,
            pk=pk,
            user=request.user
        )

        messages = conversation.messages.all()

        serializer = MessageSerializer(messages, many=True)

        return Response({
            "conversation_id": conversation.id,
            "status": conversation.status,
            "messages": serializer.data
        })

class SendMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        content = request.data.get("content")

        if not content:
            return Response(
                {"error": "Content is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # lấy conversation open gần nhất
        conversation = Conversation.objects.filter(
            user=request.user,
            status="open"
        ).first()

        # nếu chưa có → tạo mới
        if not conversation:
            conversation = Conversation.objects.create(
                user=request.user,
                status="open"
            )

        message = Message.objects.create(
            conversation=conversation,
            sender_type="user",
            content=content
        )

        return Response({
            "message_id": message.id,
            "conversation_id": conversation.id,
            "created_at": message.created_at
        })

class MarkAsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        conversation_id = request.data.get("conversation_id")

        conversation = get_object_or_404(
            Conversation,
            pk=conversation_id,
            user=request.user
        )

        conversation.messages.filter(
            sender_type="admin",
            is_read=False
        ).update(is_read=True)

        return Response({"status": "ok"})

class AdminConversationListAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        conversations = Conversation.objects.all().order_by("-created_at")
        serializer = ConversationListSerializer(
            conversations,
            many=True
        )
        return Response(serializer.data)

class AdminReplyAPIView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request):

        conversation_id = request.data.get("conversation_id")
        content = request.data.get("content")

        # ===== Validate input =====
        if not conversation_id:
            return Response(
                {"error": "conversation_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not content or not content.strip():
            return Response(
                {"error": "content cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ===== Lock conversation row (tránh race condition) =====
        conversation = get_object_or_404(
            Conversation.objects.select_for_update(),
            pk=conversation_id
        )

        # ===== Không cho reply nếu đã closed =====
        if conversation.status == "closed":
            return Response(
                {"error": "Conversation is closed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        now = timezone.now()

        # ===== Tạo message =====
        message = Message.objects.create(
            conversation=conversation,
            sender_type="admin",
            content=content.strip(),
            is_read=False  # user chưa đọc
        )

        # ===== Auto assign admin nếu chưa có =====
        if not conversation.assigned_admin:
            conversation.assigned_admin = request.user

        # ===== Update thời gian =====
        conversation.last_admin_reply_at = now
        conversation.last_message_at = now
        conversation.delete_after = now + timedelta(days=10)

        conversation.save(update_fields=[
            "assigned_admin",
            "last_admin_reply_at",
            "last_message_at",
            "delete_after",
            "updated_at",
        ])

        return Response(
            {
                "status": "sent",
                "conversation_id": conversation.id,
                "message": {
                    "id": message.id,
                    "content": message.content,
                    "sender_type": message.sender_type,
                    "created_at": message.created_at,
                },
                "delete_after": conversation.delete_after,
            },
            status=status.HTTP_201_CREATED
        )

class AdminCloseConversationAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        conversation_id = request.data.get("conversation_id")

        conversation = get_object_or_404(
            Conversation,
            pk=conversation_id
        )

        conversation.status = "closed"
        conversation.save()

        return Response({"status": "closed"})
