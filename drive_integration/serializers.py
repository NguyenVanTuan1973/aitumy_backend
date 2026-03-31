import json
from rest_framework import serializers

class CreateDocumentSerializer(serializers.Serializer):

    values = serializers.JSONField()

    evidence_file = serializers.FileField(
        required=False,
        allow_null=True
    )

    set_name = serializers.CharField(required=False, allow_blank=True)

    doc_symbol = serializers.CharField(required=False, allow_blank=True)
    doc_type = serializers.CharField(required=False, allow_blank=True)
    doc_number = serializers.CharField(required=False, allow_blank=True)

    doc_date = serializers.CharField(required=False, allow_blank=True)

    doc_content = serializers.CharField(required=False, allow_blank=True)

    total_amount = serializers.FloatField(required=False)
    tax_amount = serializers.FloatField(required=False)
    discount_amount = serializers.FloatField(required=False)
    tax_rate = serializers.FloatField(required=False)

    payment_type = serializers.CharField(required=False, allow_blank=True)

    repayment_day = serializers.CharField(required=False, allow_blank=True)

    out_in_code = serializers.CharField(required=False, allow_blank=True)

    industry_code = serializers.CharField(required=False, allow_blank=True)

    doc_register = serializers.CharField(required=False, allow_blank=True)

    job_code = serializers.CharField(required=False, allow_blank=True)

    object_code = serializers.CharField(required=False, allow_blank=True)

    accounting_code = serializers.CharField(required=False, allow_blank=True)

    def validate_values(self, values):

        if isinstance(values, str):

            try:
                values = json.loads(values)
            except Exception:

                raise serializers.ValidationError(
                    "values must be valid JSON"
                )

        if not isinstance(values, list):

            raise serializers.ValidationError(
                "values must be a list"
            )

        return values
