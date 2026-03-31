# appconfig/api.py

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from .models import SidebarMenu
from .serializers import SidebarMenuSerializer


class SidebarMenuListAPIView(ListAPIView):
    serializer_class = SidebarMenuSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # ví dụ: lọc theo module user có quyền
        return SidebarMenu.objects.filter(is_active=True).order_by("sort_order")