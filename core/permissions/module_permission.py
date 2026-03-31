from rest_framework.permissions import BasePermission
from ..services.access_control_service import AccessControlService
from users.models import Module, Organization


class ModulePermission(BasePermission):

    module_code = None
    permission_code = None

    def has_permission(self, request, view):

        if not self.module_code or not self.permission_code:
            return False

        organization_id = request.headers.get("X-Organization-ID")

        if not organization_id:
            return False

        try:
            organization = Organization.objects.get(id=organization_id)
            module = Module.objects.get(code=self.module_code)
        except:
            return False

        AccessControlService.check_full_access(
            request.user,
            organization,
            module,
            self.permission_code
        )

        return True
