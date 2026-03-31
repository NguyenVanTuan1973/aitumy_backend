from django.db import transaction
from django.core.exceptions import ValidationError

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from knowledge_base.models import AccountingRegime

from users.models import User, Organization, OrganizationMember, Plan, Subscription, PlanModule, OrganizationModule, \
    AccountingProfile, ProfileUser

from core.validators.user_validators import UserValidators


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):

        try:
            email = UserValidators.email(request.data.get("email"))
            password = UserValidators.password(request.data.get("password"))

            confirm_password = request.data.get("confirm_password")
            if confirm_password is not None:
                UserValidators.confirm_password(confirm_password, password)

        except ValidationError as e:
            return Response(
                {"error": str(e.detail[0]) if isinstance(e.detail, list) else str(e.detail)},
                status=400
            )

        name = request.data.get("name")
        tax_code = (request.data.get("tax_code") or "").strip()
        broker_code = request.data.get("broker_code")

        LEGAL_FORM_MAP = {
            "hkd": Organization.LegalForm.HKD,
            "enterprise": Organization.LegalForm.ENTERPRISE,
        }

        legal_form_input = (request.data.get("legal_form") or "").lower()
        legal_form = LEGAL_FORM_MAP.get(legal_form_input)



        if not legal_form:
            return Response({"error": "Loại hình không hợp lệ"}, status=400)

        if not email or not password or not name or not tax_code:
            return Response({"error": "Thiếu thông tin bắt buộc"}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email đã tồn tại"}, status=400)

        # 🔥 Check MST unique
        if Organization.objects.filter(tax_code=tax_code).exists():
            return Response({"error": "Mã số thuế đã tồn tại"}, status=400)


        # 1️⃣ User
        user = User.objects.create_user(
            email=email,
            password=password,
            full_name=name,
            broker_code=broker_code,
        )

        # 2️⃣ Organization (PENDING)
        organization = Organization.objects.create(
            name=name,
            tax_code=tax_code,
            legal_form=legal_form,
            status=Organization.Status.PENDING
        )

        # 3️⃣ Owner
        OrganizationMember.objects.create(
            organization=organization,
            user=user,
            role="OWNER"
        )

        # ❗ KHÔNG tạo subscription, module, accounting ở đây

        return Response({
            "message": "Đăng ký thành công",
            "require_connect_google": True
        }, status=status.HTTP_201_CREATED)


