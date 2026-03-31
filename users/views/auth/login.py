import uuid
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User, UserSession, Organization, OrganizationMember, Subscription, OrganizationModule


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):


        email = request.data.get("email")
        password = request.data.get("password")

        user_obj = User.objects.filter(email=email).first()

        if not user_obj:
            return Response(
                {"error": "Sai email hoặc mật khẩu"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user_obj.is_active:
            return Response(
                {"error": "Tài khoản đã bị khóa"},
                status=status.HTTP_403_FORBIDDEN
            )

        user = authenticate(email=email, password=password)

        if not user:
            return Response(
                {"error": "Sai email hoặc mật khẩu"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Organization (1 User = 1 Org)
        membership = (
            OrganizationMember.objects
            .select_related("organization")
            .filter(user=user, is_active=True)
            .first()
        )

        if not membership:
            return Response(
                {"error": "User chưa thuộc Organization."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        organization = membership.organization

        # 🔥 đảm bảo legal_form luôn tồn tại
        org_type = organization.legal_form or Organization.LegalForm.HKD

        # Subscription
        subscription = (
            Subscription.objects
            .select_related("plan")
            .filter(
                organization=organization,
                status=Subscription.STATUS_ACTIVE
            )
            .first()
        )

        today = timezone.now().date()

        if subscription:
            expires_at = subscription.current_period_end
            subscription_active = expires_at >= today
            days_remaining = (expires_at - today).days
            plan_code = subscription.plan.code.upper()
        else:
            subscription_active = False
            expires_at = None
            days_remaining = 0
            plan_code = None

        # Organization type lấy đúng từ model
        org_type = organization.legal_form

        # Modules
        org_modules = (
            OrganizationModule.objects
            .select_related("module")
            .filter(
                organization=organization,
                is_enabled=True
            )
        )

        modules = {}

        for m in org_modules:
            modules[m.module.code] = {
                "view": True,
                "create": True,
                "edit": True,
                "delete": True,
            }

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "session_token": record_user_session(user, request),

            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": membership.role
            },

            # 🔥 Organization luôn tồn tại
            "organization": {
                "id": organization.id,
                "name": organization.name,
                "tax_code": organization.tax_code,
                "legal_form": org_type  # dùng legal_form thay vì type cho rõ nghĩa
            },

            "subscription": {
                "plan_code": plan_code,
                "is_active": subscription_active,
                "expires_at": expires_at,
                "days_remaining": days_remaining
            },

            "modules": modules
        })


# Ghi lại thiết bị khi user đăng nhập thành công
def record_user_session(user, request):
    user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")
    ip = get_client_ip(request)
    token_id = str(uuid.uuid4())  # ID duy nhất cho thiết bị

    session = UserSession.objects.create(
        user=user,
        user_agent=user_agent,
        ip_address=ip,
        session_token=token_id
    )
    return token_id

def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip