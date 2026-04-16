from rest_framework import status, permissions, generics
from users.models import Plan
from users.serializers import PlanSerializer


class PlanListAPIView(generics.ListAPIView):
    """
    API trả về danh sách Plan đang active.
    Dùng cho màn hình upgrade. theo Org_type (hkd, hkd_plus, hkd_pro, enterprise, enterprise_plus)

    """

    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]  # hoặc IsAuthenticated nếu bạn muốn

    def get_queryset(self):
        qs = Plan.objects.filter(is_active=True)

        organization = getattr(self.request, "organization", None)

        if organization:
            if organization.legal_form == "HKD":
                qs = qs.filter(code__in=["hkd", "hkd_plus", "hkd_pro"])

            elif organization.legal_form == "ENTERPRISE":
                qs = qs.filter(code__in=["enterprise", "enterprise_plus"])

        else:
            # Guest → mặc định HKD
            qs = qs.filter(code__in=["hkd", "hkd_plus", "hkd_pro"])

        return qs.order_by("sort_order", "price")

