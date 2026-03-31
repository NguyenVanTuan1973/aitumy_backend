from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from users.models import UserSession


class SessionValidationMiddleware(MiddlewareMixin):

    def process_request(self, request):

        # 🚫 Chỉ áp dụng cho API routes
        if not request.path.startswith("/api/"):
            return None  # ✅ Đúng

        # Nếu chưa authenticate thì bỏ qua (JWT sẽ xử lý)
        if not request.user or not request.user.is_authenticated:
            return None

        session_token = request.headers.get("X-Session-Token")

        if not session_token:
            raise PermissionDenied("Session token missing")

        try:
            user_session = UserSession.objects.get(
                session_token=session_token,
                user=request.user,
                is_active=True
            )
        except UserSession.DoesNotExist:
            raise PermissionDenied("Invalid or revoked session")

        if user_session.expires_at and user_session.expires_at < timezone.now():
            user_session.is_active = False
            user_session.save(update_fields=["is_active"])
            raise PermissionDenied("Session expired")

        request.user_session = user_session

        return None

