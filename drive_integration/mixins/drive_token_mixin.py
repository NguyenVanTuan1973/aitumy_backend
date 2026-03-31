from users.models import UserDrive

from drive_integration.services.google_oauth_service import GoogleOAuthService


class DriveTokenMixin:
    """
    Đảm bảo access_token luôn hợp lệ trước khi dùng
    """

    def get_valid_access_token(self, user):
        drive = UserDrive.objects.get(user=user)

        if drive.is_expired():
            refreshed = GoogleOAuthService.refresh_access_token(
                drive.refresh_token
            )

            drive.access_token = refreshed["access_token"]
            drive.expires_at = refreshed["expires_at"]

            if refreshed.get("scope"):
                drive.scope = refreshed["scope"]

            drive.save(update_fields=[
                "access_token",
                "expires_at",
                "scope",
                "updated_at"
            ])

        return drive.access_token
