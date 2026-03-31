from django.urls import path
from .consumers import SupportConsumer

websocket_urlpatterns = [
    path("ws/support/<int:conversation_id>/", SupportConsumer.as_asgi()),
]
