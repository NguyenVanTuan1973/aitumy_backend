from django.urls import path

from .views import UserConversationListAPIView, UserConversationDetailAPIView, SendMessageAPIView, \
    MarkAsReadAPIView, AdminConversationListAPIView, AdminReplyAPIView, AdminCloseConversationAPIView

urlpatterns = [
    # user
    path("conversations/", UserConversationListAPIView.as_view()),
    path("conversations/<int:pk>/", UserConversationDetailAPIView.as_view()),
    path("messages/send/", SendMessageAPIView.as_view()),
    path("conversations/mark-read/", MarkAsReadAPIView.as_view()),

    # admin
    path("admin/conversations/", AdminConversationListAPIView.as_view()),
    path("admin/reply/", AdminReplyAPIView.as_view()),
    path("admin/close/", AdminCloseConversationAPIView.as_view()),
]