from django.db import transaction

from django.shortcuts import get_object_or_404
from rest_framework import status, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from rest_framework_simplejwt.authentication import JWTAuthentication

from users.models import UserSession, Module, Organization, OrganizationMember, OrganizationModule, AccountingProfile, Industry

from users.serializers import OrganizationUpdateSerializer, OrganizationDetailSerializer



class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {
            "user": {
                "id": request.user.id,
                "email": request.user.email,
                "full_name": request.user.full_name,
            },
            "organizations": []
        }

        memberships = OrganizationMember.objects.filter(
            user=request.user,
            is_active=True
        ).select_related("organization")

        for m in memberships:
            modules = OrganizationModule.objects.filter(
                organization=m.organization,
                is_enabled=True
            ).values_list("module__code", flat=True)

            data["organizations"].append({
                "id": m.organization.id,
                "name": m.organization.name,
                "role": m.role,
                "modules": list(modules)
            })

        return Response(data)

# API Đăng ký dữ liệu ban đầu 'Hộ kinh doanh'/'Doanh nghiệp' cho User
class CreateOrganizationAPIView(APIView):
    authentication_classes = [JWTAuthentication]  # Xác thực bằng JWT
    permission_classes = [IsAuthenticated]  # Chỉ cho phép người dùng có token

    @transaction.atomic
    def post(self, request):
        user = request.user
        name = request.data.get("name")
        tax_code = request.data.get("tax_code")
        module_code = request.data.get("module_code")

        if not all([name, tax_code, module_code]):
            return Response(
                {"error": "Thiếu dữ liệu"},
                status=400
            )

        module = Module.objects.filter(code=module_code, is_active=True).first()
        if not module:
            return Response({"error": "Module không hợp lệ"}, status=400)

        org = Organization.objects.create(
            name=name,
            tax_code=tax_code,
            owner=user
        )

        OrganizationMember.objects.create(
            user=user,
            organization=org,
            role="OWNER"
        )

        OrganizationModule.objects.create(
            organization=org,
            module=module,
            is_enabled=True
        )

        # UserModule.objects.create(
        #     user=user,
        #     organization=org,
        #     module=module,
        #     is_enabled=True
        # )

        AccountingProfile.objects.create(
            organization=org,
            name=name,
            tax_code=tax_code,
            module=module,
            accounting_regime=module.default_accounting_regime,
            owner=user
        )

        UserSession.objects.filter(
            user=user,
            is_active=True
        ).update(
            organization=org,
            active_module=module
        )

        return Response(
            {"message": "Onboarding thành công"},
            status=201
        )

class OrganizationUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        organization = get_object_or_404(
            Organization,
            pk=pk,
            is_active=True
        )

        update_serializer = OrganizationUpdateSerializer(
            organization,
            data=request.data,
            partial=True,
        )

        if update_serializer.is_valid():
            update_serializer.save()

            # 🔥 Serialize lại FULL object
            detail_serializer = OrganizationDetailSerializer(organization)

            return Response(
                detail_serializer.data,
                status=status.HTTP_200_OK
            )

        return Response(
            update_serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class OrganizationIndustriesUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        """
        Update organization industries only
        Body:
        {
            "industry_ids": [1,2,3]
        }
        """

        organization = get_object_or_404(
            Organization,
            pk=pk,
            is_active=True
        )


        if not organization.members.filter(
                user=request.user,
                is_active=True
        ).exists():
            return Response(status=403)

        industry_ids = request.data.get("industry_ids", [])

        if not isinstance(industry_ids, list):
            return Response(
                {"industry_ids": "Must be a list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        industries = Industry.objects.filter(
            id__in=industry_ids,
            is_active=True
        )

        # 🔥 Update many-to-many
        organization.industries.set(industries)

        # 🔥 reload lại object để chắc chắn M2M cập nhật
        organization.refresh_from_db()

        serializer = OrganizationDetailSerializer(organization)

        return Response(serializer.data, status=status.HTTP_200_OK)

# GÁN / BẬT / TẮT MODULE; Đăng ký / kích hoạt module
class ToggleModuleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        module_code = request.data.get("module_code")
        is_enabled = request.data.get("is_enabled", True)

        if not module_code:
            return Response(
                {"error": "module_code là bắt buộc"},
                status=400
            )

        # 🔥 LẤY ORGANIZATION QUA OrganizationMember
        member = OrganizationMember.objects.filter(
            user=request.user,
            is_active=True
        ).select_related("organization").first()

        if not member:
            return Response(
                {"error": "User không thuộc organization nào"},
                status=400
            )

        # 🔐 CHECK OWNER
        if member.role != "OWNER":
            return Response(
                {"error": "Chỉ OWNER mới được bật/tắt module"},
                status=403
            )

        organization = member.organization

        try:
            module = Module.objects.get(code=module_code)
        except Module.DoesNotExist:
            return Response(
                {"error": "Module không tồn tại"},
                status=404
            )

        obj, created = OrganizationModule.objects.get_or_create(
            organization=organization,
            module=module
        )

        obj.is_enabled = is_enabled
        obj.save()

        return Response({
            "message": "Cập nhật module thành công",
            "module": module.code,
            "enabled": obj.is_enabled,
            "created": created,
        })