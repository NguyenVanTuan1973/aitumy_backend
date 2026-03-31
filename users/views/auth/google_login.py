
from django.contrib.auth import get_user_model
from rest_framework.views import APIView

from rest_framework.response import Response
from rest_framework import status

import requests

from rest_framework_simplejwt.tokens import RefreshToken

from users.serializers import GoogleLoginSerializer

from rest_framework.permissions import AllowAny


from .login import record_user_session

User = get_user_model()


class GoogleLoginAPIView(APIView):
    authentication_classes = []  # không cần JWT
    permission_classes = [AllowAny]

    def post(self, request):

        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access_token = serializer.validated_data["access_token"]

        # verify token với Google
        resp = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if resp.status_code != 200:
            return Response(
                {"error": "Invalid Google token"},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = resp.json()

        email = data["email"]
        name = data.get("name", "")

        # create / get user
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={"full_name": name}
        )

        # tạo JWT
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "session_token": record_user_session(user, request),  # ✅ THÊM DÒNG NÀY
            "email": email,
        })