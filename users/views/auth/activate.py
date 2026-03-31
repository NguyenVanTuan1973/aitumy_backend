
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from knowledge_base.models import AccountingRegime

from ...services.onboarding_service import OnboardingService


class CompleteOnboardingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = OnboardingService.complete_onboarding(
            user=request.user
        )

        return Response({
            "success": True,
            "data": result
        })

