
from datetime import date

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from drive_integration.services.drive_workspace_service import DriveWorkspaceService
from drive_integration.services.google_oauth_service import GoogleOAuthService
from knowledge_base.models import AccountingRegime
from ..models import Organization, Subscription, Plan, AccountingProfile
from ..views.subscription.subscription import apply_plan_modules


class OnboardingService:

    @staticmethod
    @transaction.atomic
    def complete_onboarding(user, server_auth_code=None):
        """
        Chỉ xử lý onboarding hệ thống (KHÔNG xử lý Google)
        Idempotent: gọi nhiều lần không tạo trùng dữ liệu
        """

        # =========================
        # 0. GET ORGANIZATION (LOCK)
        # =========================
        org = Organization.objects.select_for_update().filter(
            members__user=user,
            members__role="OWNER"
        ).first()

        if not org:
            raise Exception("Organization not found")

        # =========================
        # 1. CHECK ĐÃ ONBOARD CHƯA ✅
        # =========================
        subscription = getattr(org, "subscription", None)

        already_onboarded = (
            org.status == Organization.Status.ACTIVE
            and subscription is not None
            and subscription.status == Subscription.STATUS_ACTIVE
            and AccountingProfile.objects.filter(organization=org).exists()
        )

        if already_onboarded:
            return {
                "status": "already_completed",
                "organization_status": org.status,
                "subscription_status": subscription.status,
            }

        # =========================
        # 2. ACTIVATE ORGANIZATION
        # =========================
        if org.status != Organization.Status.ACTIVE:
            org.mark_active()

        # =========================
        # 3. SUBSCRIPTION (IDEMPOTENT)
        # =========================
        if not subscription:
            DEFAULT_PLAN_BY_LEGAL_FORM = {
                Organization.LegalForm.HKD: "hkd",
                Organization.LegalForm.ENTERPRISE: "enterprise",
            }

            plan_code = DEFAULT_PLAN_BY_LEGAL_FORM.get(org.legal_form)

            if not plan_code:
                raise Exception("Plan not configured for legal form")

            plan = Plan.objects.get(code=plan_code, is_active=True)

            today = date.today()

            subscription = Subscription.objects.create(
                organization=org,
                plan=plan,
                current_period_start=today,
                current_period_end=today + relativedelta(months=1),
                status=Subscription.STATUS_ACTIVE
            )

            apply_plan_modules(org, plan)

        # 👉 Nếu có subscription nhưng EXPIRED → có thể nâng cấp sau
        elif subscription.status != Subscription.STATUS_ACTIVE:
            # Không tạo lại, chỉ giữ nguyên
            pass

        # =========================
        # 4. ACCOUNTING PROFILE
        # =========================
        if not AccountingProfile.objects.filter(organization=org).exists():

            regime_code = settings.DEFAULT_ACCOUNTING_REGIME_BY_TYPE.get(org.legal_form)

            if not regime_code:
                raise Exception("Accounting regime not configured")

            default_regime = AccountingRegime.objects.get(code=regime_code)

            today = date.today()

            AccountingProfile.objects.create(
                name=org.name,
                tax_code=org.tax_code,
                organization=org,
                accounting_regime=default_regime,
                fiscal_year_start=date(today.year, 1, 1),
            )

        # =========================
        # 5. USER FLAG (OPTIONAL)
        # =========================
        # 👉 Không dùng làm logic chính, chỉ để tracking
        if hasattr(user, "is_onboarded") and not user.is_onboarded:
            user.is_onboarded = True
            user.onboarded_at = timezone.now()
            user.save(update_fields=["is_onboarded", "onboarded_at"])

        return {
            "status": "completed",
            "organization_status": org.status,
            "subscription_status": subscription.status,
        }