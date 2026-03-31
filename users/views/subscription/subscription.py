from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import timedelta
from users.models import User, UserDrive, Module, OrganizationMember, Subscription, Plan, OrganizationModule


# Đăng ký ORG, Module
class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        member = OrganizationMember.objects.filter(
            user=request.user,
            is_active=True
        ).select_related("organization").first()

        if not member:
            return Response({"detail": "No organization"}, status=404)

        subscription, _ = Subscription.objects.get_or_create(
            organization=member.organization
        )

        return Response({
            "plan": {
                "code": subscription.plan.code,
                "name": subscription.plan.name,
            } if subscription.plan else None,
            "status": subscription.status,
            "organization": member.organization.name,
        })

class UpgradeSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        plan_code = request.data.get("plan")

        VALID_PLANS = ["hkd", "hkd_plus", "hkd_pro"]

        if plan_code not in VALID_PLANS:
            return Response({"detail": "Invalid plan"}, status=400)

        member = (
            OrganizationMember.objects
            .filter(user=request.user, is_active=True)
            .select_related("organization")
            .first()
        )

        if not member:
            return Response({"detail": "No organization"}, status=404)

        if member.role != "OWNER":
            return Response({"detail": "Only owner can upgrade"}, status=403)

        # 🔥 LẤY PLAN OBJECT
        plan = Plan.objects.filter(
            code__iexact=plan_code,
            is_active=True
        ).first()

        if not plan:
            return Response({"detail": "Plan not found"}, status=404)

        with transaction.atomic():

            subscription, created = Subscription.objects.get_or_create(
                organization=member.organization,
                defaults={
                    "plan": plan,
                    "current_period_start": timezone.now().date(),
                    "current_period_end": timezone.now().date() + timedelta(days=30),
                    "status": Subscription.STATUS_ACTIVE,
                }
            )

            old_plan = subscription.plan

            # 🚀 Upgrade logic
            subscription.plan = plan
            subscription.status = Subscription.STATUS_ACTIVE
            subscription.current_period_start = timezone.now().date()

            if plan.code.lower() == "hkd":
                subscription.current_period_end = None
            else:
                subscription.current_period_end = (
                    timezone.now().date() + timedelta(days=30)
                )

            subscription.save()

            # 🔥 Sync module
            apply_plan_modules(member.organization, plan.code.lower())

        return Response({
            "detail": "Upgraded successfully",
            "old_plan": old_plan.code if old_plan else None,
            "new_plan": plan.code,
            "current_period_end": subscription.current_period_end,
        })

class CancelSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        member = OrganizationMember.objects.filter(
            user=request.user,
            is_active=True
        ).select_related("organization").first()

        if not member:
            return Response({"detail": "No organization"}, status=404)

        subscription = Subscription.objects.filter(
            organization=member.organization
        ).first()

        if not subscription:
            return Response({"detail": "No subscription"}, status=404)

        subscription.status = "canceled"
        subscription.save()

        # Downgrade về free
        self._apply_plan_modules(member.organization, "free")

        return Response({"detail": "Canceled successfully"})

    def _apply_plan_modules(self, organization, plan):

        plan_modules = {
            "free": ["ACCOUNTING_BASIC"],
            "pro": ["ACCOUNTING_BASIC", "INVENTORY"],
            "enterprise": ["ACCOUNTING_BASIC", "INVENTORY", "HRM"],
        }

        allowed = plan_modules.get(plan, [])

        for org_module in organization.organization_modules.all():
            org_module.is_enabled = org_module.module.code in allowed
            org_module.save()

def apply_plan_modules(organization, plan):

        PLAN_MODULE_MAP = {
            "hkd": [
                "DASHBOARD",
            ],
            "hkd_plus": [
                "DASHBOARD",
                "ACCOUNTING_HKD",
                "REPORT_BASIC",
            ],
            "hkd_pro": [
                "DASHBOARD",
                "ACCOUNTING_DN",
                "REPORT_ADVANCED",
                "INVENTORY",
                "PAYROLL",
            ],
        }

        module_codes = PLAN_MODULE_MAP.get(plan, [])

        if not module_codes:
            return

        with transaction.atomic():

            # 1️⃣ Disable tất cả module hiện tại
            OrganizationModule.objects.filter(
                organization=organization
            ).update(is_enabled=False)

            # 2️⃣ Lấy module object theo code
            modules = Module.objects.filter(code__in=module_codes)

            for module in modules:
                org_module, created = OrganizationModule.objects.get_or_create(
                    organization=organization,
                    module=module,
                    defaults={
                        "is_enabled": True,
                        "activated_at": timezone.now(),
                    }
                )

                if not created:
                    org_module.is_enabled = True
                    org_module.activated_at = timezone.now()
                    org_module.save()