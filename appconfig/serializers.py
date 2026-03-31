
from rest_framework import serializers
from .models import SidebarMenu


class SidebarMenuSerializer(serializers.ModelSerializer):

    module_code = serializers.CharField(
        source="module.code",
        allow_null=True
    )

    app_module = serializers.CharField(
        source="app_module.code"
    )

    class Meta:
        model = SidebarMenu
        fields = [
            "id",
            "title",
            "icon",
            "app_module",
            "action",
            "module_code",
        ]