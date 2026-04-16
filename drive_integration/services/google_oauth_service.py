import json
import base64
import requests

from datetime import timedelta
from django.conf import settings
from django.utils import timezone

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from users.models import UserDrive


class GoogleOAuthService:
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    # ==================================================
    # 1️⃣ BUILD GOOGLE OAUTH URL (LOGIN / CONSENT)
    # ==================================================
    # def build_auth_url(self, *, user, scopes, mode: str) -> str:
    #     """
    #     Build Google OAuth consent URL
    #     """
    #
    #     state_payload = {
    #         "user_id": user.id,
    #         "mode": mode,
    #     }
    #
    #     state = base64.urlsafe_b64encode(
    #         json.dumps(state_payload).encode()
    #     ).decode()
    #
    #     flow = Flow.from_client_secrets_file(
    #         settings.GOOGLE_OAUTH_CLIENT_SECRET_FILE,
    #         scopes=scopes,
    #         redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI,
    #     )
    #
    #     auth_url, _ = flow.authorization_url(
    #         access_type="offline",
    #         include_granted_scopes="true",
    #         prompt="consent",
    #         state=state,
    #     )
    #
    #     return auth_url

    # ==================================================
    # 2️⃣ EXCHANGE CODE → TOKEN (CALLBACK)
    # ==================================================
    def exchange_code_for_token(self, *, code: str):
        response = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise Exception("GOOGLE_TOKEN_EXCHANGE_FAILED")

        data = response.json()

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_at": timezone.now() + timedelta(seconds=data["expires_in"]),
            "scope": data.get("scope"),
        }

    # ==================================================
    # 3️⃣ REFRESH TOKEN (GIỮ NGUYÊN)
    # ==================================================
    @classmethod
    def refresh_access_token(cls, refresh_token: str):
        response = requests.post(
            cls.TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=10,
        )

        if response.status_code != 200:
            # LOG LỖI RA ĐỂ KIỂM TRA
            print(f"Google Refresh Error: {response.text}")
            raise Exception("FAILED_TO_REFRESH_GOOGLE_ACCESS_TOKEN")

        data = response.json()
        return {
            "access_token": data["access_token"],
            "expires_at": timezone.now() + timedelta(seconds=data["expires_in"]),
        }

    """
    @classmethod
    def refresh_access_token(cls, refresh_token: str):
        response = requests.post(
            cls.TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise Exception("FAILED_TO_REFRESH_GOOGLE_ACCESS_TOKEN")

        data = response.json()

        return {
            "access_token": data["access_token"],
            "expires_at": timezone.now() + timedelta(seconds=data["expires_in"]),
            "scope": data.get("scope"),
        }
        
    """

    # ==================================================
    # 4️⃣ GET USER CREDENTIALS (🔥 QUAN TRỌNG 🔥)
    # ==================================================
    @classmethod
    def get_credentials_for_user(cls, *, user):
        """
        Trả về google.oauth2.credentials.Credentials
        Dùng cho Drive API / Sheets API
        """

        user_drive = UserDrive.objects.filter(user=user).first()
        if not user_drive:
            raise Exception("USER_NOT_CONNECTED_GOOGLE")

        # ⏰ refresh nếu hết hạn
        if (
                user_drive.token_expiry
                and user_drive.token_expiry <= timezone.now()
        ):
            if not user_drive.refresh_token:
                raise Exception("GOOGLE_REFRESH_TOKEN_MISSING")

            refreshed = cls.refresh_access_token(
                user_drive.refresh_token
            )

            user_drive.access_token = refreshed["access_token"]
            user_drive.token_expiry = refreshed["expires_at"]
            user_drive.save(update_fields=["access_token", "token_expiry"])

        return Credentials(
            token=user_drive.access_token,
            refresh_token=user_drive.refresh_token,
            token_uri=cls.TOKEN_URL,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )

