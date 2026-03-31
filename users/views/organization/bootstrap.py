from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from users.models import User, UserDrive, UserSession, Module, Organization, OrganizationMember, \
    OrganizationModule, MemberModulePermission, ModulePermission, AccountingProfile, Subscription, PlanModule, \
    ProfileUser, Plan, Industry


from users.serializers import IndustrySerializer, PlanSerializer

from users.utils.drive_status import get_drive_status
from users.serializers import OrganizationBootstrapSerializer, UserBootstrapSerializer
from appconfig.models import AppModule, SidebarMenu
from accounting.models import Regulation, AccountType, Account
from accounting.serializers import AccountSerializer

from appconfig.serializers import SidebarMenuSerializer



# Kiểm tra User sau khi login là Cũ/Mới, đã thiết lập Organization chưa ?
class BootstrapSessionAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        membership = (
            OrganizationMember.objects
            .select_related("organization")
            .filter(user=user, is_active=True)
            .first()
        )

        if not membership:
            return Response(
                {"error": "User chưa có Organization"},
                status=500
            )

        organization = membership.organization

        if not organization.legal_form:
            organization.legal_form = Organization.LegalForm.HKD

        org_data = OrganizationBootstrapSerializer(
            organization,
            context={"user": user}
        ).data

        drive_status = get_drive_status(user, organization)

        # ==================================================
        # 🔥 PLANS (THEO LEGAL_FORM)
        # ==================================================

        plans_qs = Plan.objects.filter(is_active=True)

        if organization.legal_form == Organization.LegalForm.HKD:
            plans_qs = plans_qs.filter(code__in=["hkd", "hkd_plus", "hkd_pro"])

        elif organization.legal_form == Organization.LegalForm.ENTERPRISE:
            plans_qs = plans_qs.filter(code__in=["enterprise", "enterprise_plus"])

        plans_data = PlanSerializer(
            plans_qs.order_by("sort_order", "price"),
            many=True
        ).data

        # ==================================================
        # SUBSCRIPTION
        # ==================================================
        subscription_data = None
        subscription = getattr(organization, "subscription", None)

        allowed_module_ids = []

        if subscription:
            plan = subscription.plan

            subscription_data = {
                "plan": {
                    "code": plan.code,
                    "name": plan.name,
                    "max_users": plan.max_users,
                    "max_documents_per_month": plan.max_documents_per_month,
                },
                "status": subscription.status,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
            }

            # 🔥 Lấy module được phép theo plan
            allowed_module_ids = (
                plan.planmodule_set
                .values_list("module_id", flat=True)
            )

        # ==================================================
        # 🔥 APP MODULES + SIDEBAR MENUS
        # ==================================================

        app_modules_qs = (
            AppModule.objects
            .filter(is_active=True)
            .order_by("sort_order")
        )

        sidebar_qs = (
            SidebarMenu.objects
            .filter(is_active=True)
            .filter(
                Q(feature_module__isnull=True) |
                Q(feature_module_id__in=allowed_module_ids)
            )
            .select_related("app_module", "feature_module")
            .order_by("app_module__sort_order", "sort_order")
        )

        # Group menu theo AppModule
        menus_grouped = {}

        for menu in sidebar_qs:
            module_code = menu.app_module.code

            if module_code not in menus_grouped:
                menus_grouped[module_code] = {
                    "app_module": {
                        "code": menu.app_module.code,
                        "name": menu.app_module.name,
                    },
                    "items": []
                }

            menus_grouped[module_code]["items"].append(
                SidebarMenuSerializer(menu).data
            )

        menus_response = list(menus_grouped.values())

        # ==================================================
        # 9️⃣ 🔥 ALL INDUSTRIES (NGÀNH NGHỀ)
        # Chỉ dùng cho hkd_plus và hkd_pro
        # ==================================================
        plan_code = subscription.plan.code if subscription else None

        industries_data = []

        if plan_code in ["hkd_plus", "hkd_pro"]:
            industries_data = IndustrySerializer(
                Industry.objects.filter(is_active=True),
                many=True
            ).data

        # ==================================================
        # 🔥 DANH MỤC TÀI KHOẢN THEO TT 99
        # Chỉ dùng cho hkd_pro / enterprise
        # ==================================================
        accounts_payload = {}

        plan_code = subscription.plan.code if subscription else None

        if plan_code in ["hkd_pro", "enterprise"]:
            regulation = Regulation.objects.filter(
                code="99/2025/TT-BTC"
            ).first()

            accounts_qs = (
                Account.objects
                .filter(regulation=regulation, is_active=True)
                .select_related("parent")
                .prefetch_related("children")
            )

            # --------------------------------------------------
            # 1️⃣ TK 333 tree (thuế)
            # --------------------------------------------------

            tax_accounts = accounts_qs.filter(code="333")

            # --------------------------------------------------
            # 2️⃣ Revenue accounts
            # --------------------------------------------------

            revenue_accounts = accounts_qs.filter(
                account_type=AccountType.REVENUE
            )

            # --------------------------------------------------
            # 3️⃣ Expense tree (642)
            # --------------------------------------------------

            expense_accounts = accounts_qs.filter(code="642")

            # --------------------------------------------------
            # 4️⃣ Cash & Bank
            # --------------------------------------------------

            cash_accounts = accounts_qs.filter(
                code__in=["111", "112"]
            )

            # --------------------------------------------------
            # 5️⃣ Receivable
            # --------------------------------------------------

            receivable_accounts = accounts_qs.filter(
                code="131"
            )

            # --------------------------------------------------
            # 6️⃣ VAT deductible (2 cấp)
            # --------------------------------------------------

            vat_deductible_accounts = accounts_qs.filter(
                code="133"
            )

            # --------------------------------------------------
            # 7️⃣ Inventory
            # --------------------------------------------------

            inventory_accounts = accounts_qs.filter(
                code__in=["152", "153", "156"]
            )

            # --------------------------------------------------
            # 8️⃣ Payable
            # --------------------------------------------------

            payable_accounts = accounts_qs.filter(
                code="331"
            )

            # --------------------------------------------------
            # 9️⃣ Equity (2 cấp)
            # --------------------------------------------------

            equity_accounts = accounts_qs.filter(
                code="411"
            )

            # --------------------------------------------------
            # PAYLOAD
            # --------------------------------------------------

            accounts_payload = {
                "tax_accounts": AccountSerializer(tax_accounts, many=True).data,
                "revenue_accounts": AccountSerializer(revenue_accounts, many=True).data,
                "expense_accounts": AccountSerializer(expense_accounts, many=True).data,

                "cash_accounts": AccountSerializer(cash_accounts, many=True).data,
                "receivable_accounts": AccountSerializer(receivable_accounts, many=True).data,
                "vat_deductible_accounts": AccountSerializer(vat_deductible_accounts, many=True).data,
                "inventory_accounts": AccountSerializer(inventory_accounts, many=True).data,
                "payable_accounts": AccountSerializer(payable_accounts, many=True).data,
                "equity_accounts": AccountSerializer(equity_accounts, many=True).data,
            }

        return Response({
            "user": UserBootstrapSerializer(user).data,
            "has_organization": True,
            "organization": org_data,
            "plans": plans_data,
            "onboarding_completed": True,
            "drive_status": drive_status,
            "subscription": subscription_data,
            "menus": menus_response,
            "all_industries": industries_data,
            "accounts": accounts_payload,
        })