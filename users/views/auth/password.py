import secrets
import string

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from users.models import User

User = get_user_model()

class ForgotPasswordView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        email = request.data.get("email", "").strip()

        # 1️⃣ Kiểm tra email rỗng
        if not email:
            return Response(
                {"error": "Email không được để trống"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2️⃣ Validate email format
        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {"error": "Email không hợp lệ"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3️⃣ Tìm user
        user = User.objects.filter(email=email).first()

        if not user:
            return Response(
                {"error": "Không tìm thấy tài khoản với email này"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 4️⃣ Tạo password random
        new_password = self._generate_random_password()

        # 5️⃣ Cập nhật password
        user.set_password(new_password)
        user.save(update_fields=["password"])

        # 6️⃣ Gửi email

        try:

            send_mail(
                subject="Mật khẩu mới của bạn",
                message=(
                    f"Mật khẩu mới của bạn là: {new_password}\n\n"
                    "Vui lòng đăng nhập và đổi lại mật khẩu sau khi đăng nhập."
                ),
                from_email="support@aitumy.online",
                recipient_list=[email],
                fail_silently=False,
            )



        except Exception:
            return Response(
                {"error": "Không thể gửi email. Vui lòng thử lại sau."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "Nếu email tồn tại, mật khẩu mới đã được gửi"},
            status=status.HTTP_200_OK,
        )


    def _generate_random_password(self, length=12):

        import secrets
        import string

        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*()-_=+"

        # đảm bảo có đủ các loại ký tự
        password_chars = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special),
        ]

        # phần còn lại random
        all_chars = lowercase + uppercase + digits + special

        password_chars += [
            secrets.choice(all_chars)
            for _ in range(length - 4)
        ]

        # xáo trộn password
        secrets.SystemRandom().shuffle(password_chars)

        return "".join(password_chars)

class ChangePasswordView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        user = request.user

        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return Response(
                {"error": "Vui lòng cung cấp đầy đủ mật khẩu cũ và mới"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # kiểm tra mật khẩu cũ
        if not user.check_password(old_password):
            return Response(
                {"error": "Mật khẩu cũ không chính xác"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # validate password theo chuẩn Django
        try:
            validate_password(new_password, user)

        except ValidationError as e:
            return Response(
                {"error": e.messages[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # cập nhật password
        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Mật khẩu đã được cập nhật thành công"},
            status=status.HTTP_200_OK,
        )

