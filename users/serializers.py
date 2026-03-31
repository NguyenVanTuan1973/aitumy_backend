from rest_framework import serializers
from .models import Module, Organization, OrganizationMember, OrganizationModule, PlanModule, Plan, Industry, \
    OrganizationIndustry
from django.contrib.auth import get_user_model

from appconfig.models import AppModule, SidebarMenu

User = get_user_model()

class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ["code", "name", "description"]

class OrganizationSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    tax_code = serializers.CharField()
    address = serializers.CharField()
    legal_form = serializers.CharField()
    plan = serializers.CharField()
    modules = serializers.ListField(child=serializers.CharField())
    subscription_valid = serializers.BooleanField()

class UserProfileSerializer(serializers.ModelSerializer):
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "organizations"]

    def get_organizations(self, user):
        memberships = OrganizationMember.objects.filter(
            user=user,
            is_active=True,
            organization__is_active=True
        ).select_related("organization")

        result = []

        for member in memberships:
            org = member.organization

            # 🔎 Lấy subscription
            subscription = getattr(org, "subscription", None)

            if not subscription or not subscription.is_valid():
                subscription_valid = False
                plan_code = None
                base_modules = []
            else:
                subscription_valid = True
                plan_code = subscription.plan.code

                # 📦 Module từ Plan
                base_modules = list(
                    PlanModule.objects.filter(
                        plan=subscription.plan,
                        module__is_active=True
                    ).values_list("module__code", flat=True)
                )

            # 🔁 Override module theo Organization
            org_overrides = OrganizationModule.objects.filter(
                organization=org
            )

            for override in org_overrides:
                if override.is_enabled:
                    if override.module.code not in base_modules:
                        base_modules.append(override.module.code)
                else:
                    if override.module.code in base_modules:
                        base_modules.remove(override.module.code)

            result.append({
                "id": org.id,
                "name": org.name,
                "tax_code": org.tax_code,
                "address": org.address,
                "legal_form": org.legal_form,
                "plan": plan_code,
                "modules": base_modules,
                "subscription_valid": subscription_valid
            })

        return result

class CreateOrganizationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    tax_code = serializers.CharField(max_length=50)
    address = serializers.CharField(required=False, allow_blank=True)
    module_code = serializers.CharField()

# KIỂM TRA ORGANIZATION CỦA UER SAU KHI ĐĂNG NHẬP THÀNH CÔNG
class UserBootstrapSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "full_name")

class OrganizationBootstrapSerializer(serializers.Serializer):
    """
    Unified Organization serializer for Bootstrap
    Works for:
    - DB Organization
    - Public (virtual) Organization
    """

    id = serializers.IntegerField()
    name = serializers.CharField()
    tax_code = serializers.CharField()
    address = serializers.CharField()
    type = serializers.CharField()
    role = serializers.CharField(allow_null=True)
    modules = serializers.ListField()

    organization_industries = 'OrganizationIndustrySerializer(many=True,read_only=True)'

    def to_representation(self, instance):
        user = self.context.get("user")

        # ==================================================
        # 1️⃣ PUBLIC / INDIVIDUAL ORGANIZATION (VIRTUAL)
        # ==================================================
        if instance is None:
            # modules = self.context.get("modules", [])

            return {
                "id": 0,
                "name": "Cá nhân",
                "tax_code": "",
                "address": "",
                "type": Organization.LegalForm.HKD,
                "role": "MEMBER",
                # "modules": modules,
                "organization_industries": [],
            }

        # ==================================================
        # 2️⃣ REAL ORGANIZATION (DB)
        # ==================================================

        # --- ROLE ---
        role = None
        if user and user.is_authenticated:
            member = (
                OrganizationMember.objects
                .filter(
                    organization=instance,
                    user=user,
                    is_active=True
                )
                .first()
            )
            role = member.role if member else None

        # --- MODULES ---
        qs = (
            OrganizationModule.objects
            .filter(
                organization=instance,
                is_enabled=True
            )
            .select_related("module")
        )

        modules = [
            ModuleBootstrapSerializer(om.module).data
            for om in qs
        ]

        # --- INDUSTRIES ---
        org_industries_qs = (
            OrganizationIndustry.objects
            .filter(
                organization=instance,
                is_active=True
            )
            .select_related("industry")
        )

        organization_industries = OrganizationIndustrySerializer(
            org_industries_qs,
            many=True
        ).data

        return {
            "id": instance.id,
            "name": instance.name,
            "tax_code": instance.tax_code,
            "address": instance.address,
            "type": instance.legal_form.lower(),
            "role": role,
            "modules": modules,
            "organization_industries": organization_industries,
        }

class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = [
            "id",
            "code",
            "name",
            "vat_percent",
            "pit_percent",
        ]
        read_only_fields = fields

class OrganizationIndustrySerializer(serializers.ModelSerializer):
    industry = IndustrySerializer()

    class Meta:
        model = OrganizationIndustry
        fields = [
            "id",
            "industry",
            "is_active",
        ]

class ModuleBootstrapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ("id", "code", "name")

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id",
            "code",
            "name",
            "description",
            "price",
            "max_users",
            "max_documents_per_month",
            "is_highlighted",
        ]

class AppModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppModule
        fields = [
            "code",
            "name",
            "sort_order",
        ]

class SidebarMenuSerializer(serializers.ModelSerializer):

    module_code = serializers.SerializerMethodField()

    class Meta:
        model = SidebarMenu
        fields = [
            "code",
            "title",
            "icon",
            "action",
            "module_code",
        ]

    def get_module_code(self, obj):
        if obj.feature_module:
            return obj.feature_module.code.upper()
        return None

class OrganizationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "name",
            "address",
            "tax_code",
        ]

    def validate_tax_code(self, value):
        """
        Đảm bảo tax_code unique khi update
        """
        if not value:
            return value

        instance = self.instance
        exists = Organization.objects.filter(
            tax_code=value
        ).exclude(id=instance.id).exists()

        if exists:
            raise serializers.ValidationError(
                "Mã số thuế đã tồn tại."
            )

        return value

class OrganizationDetailSerializer(serializers.ModelSerializer):
    organization_industries = OrganizationIndustrySerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "address",
            "tax_code",
            "legal_form",
            "organization_industries",  # 👈 ĐỔI Ở ĐÂY
            "created_at",
            "updated_at",
            "is_active",
        ]

from rest_framework import serializers

class GoogleLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField()

class CompleteOnboardingSerializer(serializers.Serializer):
    server_auth_code = serializers.CharField(required=True)
    requested_capabilities = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )




