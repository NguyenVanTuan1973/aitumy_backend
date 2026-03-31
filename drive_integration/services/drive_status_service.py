from django.utils import timezone
from users.models import UserDrive, OrganizationModule



class DriveStatusService:
    def __init__(self, user, organization=None):
        self.user = user
        self.organization = organization
        self._drive = None

    # ==================================================
    # CORE
    # ==================================================
    def get_status(self):
        drive = self._get_drive()
        if drive is None:
            return "not_connected"

        if not drive.access_token:
            return "not_connected"

        if drive.token_expiry and drive.token_expiry <= timezone.now():
            return "expired"

        # FREE user có thể chưa có folder
        if not drive.drive_folder_id:
            return "locked"

        return "ready"

    # ==================================================
    # VIEW CONTRACT
    # ==================================================
    def is_initialized(self) -> bool:
        status = self.get_status()

        if self.organization is None:
            # FREE user: chỉ cần token là đủ
            return status in ("locked", "ready")

        return status == "ready"

    def serialize(self) -> dict:
        status = self.get_status()
        drive = self._get_drive()

        sheet_enabled = status in ("locked", "ready")

        return {
            "status": status,
            "owner": "organization" if self.organization else "user",

            "drive": {
                "enabled": False if self.organization is None else True,
                "folder_id": getattr(drive, "drive_folder_id", None),
            },

            "sheet": {
                "enabled": sheet_enabled,
                "spreadsheet_id": getattr(drive, "drive_folder_id", None),
            },
        }


    # ==================================================
    # INTERNAL
    # ==================================================
    def _get_drive(self):
        if self._drive is not None:
            return self._drive

        try:
            self._drive = UserDrive.objects.get(user=self.user)
        except UserDrive.DoesNotExist:
            self._drive = None

        return self._drive


