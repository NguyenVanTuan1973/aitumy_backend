from django.db import models
from users.models import User


class Conversation(models.Model):

    STATUS_CHOICES = (
        ("open", "Open"),
        ("closed", "Closed"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="conversations",
        db_index=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
        db_index=True
    )

    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True
    )

    # 🔥 thêm 2 field quan trọng
    last_admin_reply_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True
    )

    delete_after = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Message(models.Model):

    SENDER_CHOICES = (
        ("user", "User"),
        ("admin", "Admin"),
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=True
    )

    sender_type = models.CharField(
        max_length=10,
        choices=SENDER_CHOICES,
        db_index=True
    )

    content = models.TextField()   # 🔥 bạn đang thiếu field này

    is_read = models.BooleanField(
        default=False,
        db_index=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["conversation", "is_read"]),
        ]


