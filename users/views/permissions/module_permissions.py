from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from users.models import User, Organization, OrganizationMember, ModulePermission, MemberModulePermission


class CreateMemberAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):
        org_id = request.data.get("organization_id")
        email = request.data.get("email")
        full_name = request.data.get("full_name")

        organization = Organization.objects.get(id=org_id)

        if not is_owner(request.user, organization):
            return Response({"error": "Không có quyền"}, status=403)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"full_name": full_name}
        )

        OrganizationMember.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={"role": "MEMBER"}
        )

        return Response({"message": "Thêm thành viên thành công"})

# API QUẢN LÝ QUYỀN (CHO OWNER)
class AssignModulePermissionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        member_id = request.data["member_id"]
        module_code = request.data["module_code"]
        permission_code = request.data["permission_code"]
        is_allowed = request.data.get("is_allowed", True)

        member = OrganizationMember.objects.get(id=member_id)

        if not is_owner(request.user, member.organization):
            return Response({"error": "Không có quyền"}, status=403)

        permission = ModulePermission.objects.get(
            module__code=module_code,
            code=permission_code
        )

        obj, _ = MemberModulePermission.objects.get_or_create(
            member=member,
            permission=permission
        )
        obj.is_allowed = is_allowed
        obj.save()

        return Response({"message": "Cập nhật quyền thành công"})

# API PROFILE TRẢ VỀ QUYỀN (CHO FLUTTER)
def get_member_permissions(member):

    data = {}

    perms = MemberModulePermission.objects.filter(
        member=member,
        is_allowed=True
    ).select_related("permission", "permission__module")

    for p in perms:
        module_code = p.permission.module.code
        data.setdefault(module_code, []).append(p.permission.code)

    return data

# Helper kiểm tra quyền
def is_owner(user, organization):
    return OrganizationMember.objects.filter(
        user=user,
        organization=organization,
        role='OWNER',
        is_active=True
    ).exists()

# HELPER CHECK PERMISSION
def has_module_permission(user, organization, module_code, permission_code):
    # OWNER → full quyền
    if OrganizationMember.objects.filter(
        user=user,
        organization=organization,
        role="OWNER",
        is_active=True
    ).exists():
        return True

    return MemberModulePermission.objects.filter(
        member__user=user,
        member__organization=organization,
        member__is_active=True,
        permission__module__code=module_code,
        permission__code=permission_code,
        is_allowed=True
    ).exists()