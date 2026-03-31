from django.core.exceptions import PermissionDenied
from users.models import (
    OrganizationMember,
    OrganizationModule,
    MemberModulePermission,
    UserModule,
)


class AccessControlService:

    # ===============================
    # 1️⃣ USER LEVEL
    # ===============================
    @staticmethod
    def ensure_user_active(user):
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required")

        if not user.is_active:
            raise PermissionDenied("User account is disabled")

    # ===============================
    # 2️⃣ ORGANIZATION LEVEL
    # ===============================
    @staticmethod
    def ensure_member_of_organization(user, organization):
        if not OrganizationMember.objects.filter(
            user=user,
            organization=organization,
            is_active=True
        ).exists():
            raise PermissionDenied("User is not a member of this organization")

    @staticmethod
    def ensure_organization_module_enabled(organization, module):
        if not OrganizationModule.objects.filter(
            organization=organization,
            module=module,
            is_active=True
        ).exists():
            raise PermissionDenied("Module not enabled for this organization")

    # ===============================
    # 3️⃣ MODULE LEVEL
    # ===============================
    @staticmethod
    def ensure_user_module_enabled(user, module):
        if not UserModule.objects.filter(
            user=user,
            module=module,
            is_active=True
        ).exists():
            raise PermissionDenied("Module not enabled for user")

    # ===============================
    # 4️⃣ PERMISSION LEVEL
    # ===============================
    @staticmethod
    def ensure_member_permission(user, organization, module, permission_code):

        member = OrganizationMember.objects.filter(
            user=user,
            organization=organization,
            is_active=True
        ).first()

        if not member:
            raise PermissionDenied("Not organization member")

        # OWNER bypass
        if member.role == "OWNER":
            return True

        has_permission = MemberModulePermission.objects.filter(
            member=member,
            module=module,
            permission__code=permission_code,
            is_active=True
        ).exists()

        if not has_permission:
            raise PermissionDenied(
                f"Missing permission: {permission_code}"
            )

        return True

    # ===============================
    # 🚀 MASTER CHECK
    # ===============================
    @staticmethod
    def check_full_access(
        user,
        organization,
        module,
        permission_code
    ):
        AccessControlService.ensure_user_active(user)
        AccessControlService.ensure_member_of_organization(user, organization)
        AccessControlService.ensure_organization_module_enabled(
            organization, module
        )
        AccessControlService.ensure_user_module_enabled(user, module)
        AccessControlService.ensure_member_permission(
            user, organization, module, permission_code
        )
