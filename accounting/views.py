import os

from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import OrganizationMember

from .services.register_query import query_sheet_data
from .services.register_service import generate_register_pdf
from documents.models import RegisterMapping


class RegisterGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        params = request.data.get("params", {})

        plan_code = params.get("plan_code")
        flow = params.get("flow")
        period_type = params.get("period_type")

        year = params.get("year")
        month = params.get("month")
        quarter = params.get("quarter")

        if not plan_code or not flow:
            return Response(
                {"error": "plan_code and flow are required"},
                status=400
            )

        # =========================
        # 1️⃣ GET REGISTER TEMPLATE
        # =========================

        try:
            mapping = (
                RegisterMapping.objects
                .select_related("form_template")
                .get(
                    plan_code=plan_code,
                    flow=flow,
                    is_active=True
                )
            )
        except RegisterMapping.DoesNotExist:
            return Response(
                {"error": "Register mapping not found"},
                status=404
            )

        form_template = mapping.form_template
        form_code = form_template.code

        # =========================
        # 2️⃣ GET ORGANIZATION
        # =========================

        membership = (
            request.user.memberships
            .filter(is_active=True)
            .select_related("organization")
            .first()
        )

        if not membership:
            return Response(
                {"error": "User has no organization"},
                status=403
            )

        organization = membership.organization

        # =========================
        # 3️⃣ GET GOOGLE SHEET
        # =========================

        try:
            sheet_node = (
                request.user.drive.nodes
                .filter(node_type="sheet")
                .first()
            )

            if not sheet_node:
                return Response(
                    {"error": "Google Sheet not found"},
                    status=400
                )

            sheet_id = sheet_node.sheet_id

        except Exception:
            return Response(
                {"error": "Cannot get sheet_id"},
                status=500
            )

        # =========================
        # 4️⃣ QUERY DATA
        # =========================

        rows = query_sheet_data(
            user=request.user,
            sheet_id=sheet_id,
            doc_register=form_code,
            period_type=period_type,
            year=year,
            month=month,
            quarter=quarter
        )

        # =========================
        # 5️⃣ GENERATE FILE NAME
        # =========================

        if period_type == "month":
            period_suffix = f"{year}_{month}"
        elif period_type == "quarter":
            period_suffix = f"{year}_Q{quarter}"
        else:
            period_suffix = f"{year}"

        # =========================
        # 6️⃣ GENERATE PDF
        # =========================

        os.makedirs("media/exports", exist_ok=True)

        file_path = f"media/exports/register_{form_code}_{period_suffix}.pdf"

        pdf = generate_register_pdf(
            organization=organization,
            rows=rows,
            form_code=form_code,
            year=year,
            file_path=file_path
        )

        return FileResponse(
            open(pdf, "rb"),
            as_attachment=True,
            filename=os.path.basename(pdf),
            content_type="application/pdf",
        )


