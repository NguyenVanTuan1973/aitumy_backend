from rest_framework import serializers
from .models import Account


class AccountSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            "id",
            "code",
            "name",
            "account_type",
            "normal_balance",
            "level",
            "parent",
            "children",
        ]

    def get_children(self, obj):
        children = obj.children.all().order_by("code")
        return AccountSerializer(children, many=True).data