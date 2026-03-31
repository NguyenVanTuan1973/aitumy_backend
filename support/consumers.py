import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Conversation, Message


class SupportConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"support_{self.conversation_id}"

        if self.user.is_anonymous:
            await self.close()
            return

        # kiểm tra user có quyền vào conversation này không
        if not await self.user_has_access():
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get("content")

        message = await self.save_message(content)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    @sync_to_async
    def user_has_access(self):
        return Conversation.objects.filter(
            id=self.conversation_id,
            user=self.user
        ).exists() or self.user.is_staff

    @sync_to_async
    def save_message(self, content):
        conversation = Conversation.objects.get(id=self.conversation_id)

        message = Message.objects.create(
            conversation=conversation,
            sender_type="admin" if self.user.is_staff else "user",
            content=content
        )

        return {
            "id": message.id,
            "sender_type": message.sender_type,
            "content": message.content,
            "created_at": message.created_at.isoformat()
        }
