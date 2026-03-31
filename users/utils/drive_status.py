from users.models import UserDrive

def get_drive_status(user, organization=None):
    pass
    """
    organization để future-proof (Drive theo Org sau này)
    """


    # 2️⃣ CONNECTED / DISCONNECTED
    try:
        drive = UserDrive.objects.get(user=user)

        if not drive.access_token:
            raise UserDrive.DoesNotExist

        return {
            "status": "connected",
            "email": getattr(drive, "google_email", None),
            "connected_at": drive.created_at,
        }

    except UserDrive.DoesNotExist:
        return {
            "status": "disconnected"
        }
