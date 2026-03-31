import os
from django.conf import settings
import time
from .report_type import ReportType
from .userfree_sheet_export_pdf import UserFreeSheetExportPDF
from .hkd_income_sheet_export_pdf import HKDIncomeSheetExportPDF
from .hkd_expense_sheet_export_pdf import HKDExpenseSheetExportPDF

def _get_user_display_name(user):
    """
    Lấy tên hiển thị an toàn cho mọi loại User model
    """
    if hasattr(user, "get_full_name"):
        name = user.get_full_name()
        if name:
            return name

    if hasattr(user, "full_name") and user.full_name:
        return user.full_name

    return user.email

def export_pdf_by_type(*, report_type, user, organization, params: dict) -> str:
    """
    Điều phối export PDF theo ReportType
    """
    print("\n===== RUN: export_pdf_by_type =====")

    period_type = params.get("period_type")
    year = params.get("year")
    month = params.get("month")
    quarter = params.get("quarter")

    # ==========================================================
    # VALIDATION
    # ==========================================================
    if not period_type:
        raise ValueError("Thiếu period_type")

    if not year:
        raise ValueError("Thiếu year")

    # ==========================================================
    # TẠO FILE PATH
    # ==========================================================
    export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
    os.makedirs(export_dir, exist_ok=True)

    # filename = f"{report_type.value}_{year}.pdf"
    timestamp = int(time.time())
    filename = f"{report_type}_{year}_{timestamp}.pdf"

    file_path = os.path.join(export_dir, filename)

    print("Export file_path:", file_path)

    # ==========================================================
    # FREE USER (organization = None)
    # ==========================================================

    if organization is None:

        if report_type == ReportType.INDIVIDUAL_INCOME:
            sheet_type = "income"

            exporter = UserFreeSheetExportPDF(
                file_path=file_path,
                user=user,
                sheet_type=sheet_type,
            )

        elif report_type == ReportType.INDIVIDUAL_EXPENSE:
            sheet_type = "expense"

            exporter = UserFreeSheetExportPDF(
                file_path=file_path,
                user=user,
                sheet_type=sheet_type,
            )

        # 🔥 ACCOUNTING REGISTER
        elif report_type == ReportType.ACCOUNTING_REGISTER:

            return export_register_pdf(
                file_path=file_path,
                user=user,
                params=params,
            )

        else:
            raise ValueError("User FREE không hỗ trợ report này")

        owner_name = _get_user_display_name(user)

        result_path = exporter.export(
            owner_name=owner_name,
            address="",
            tax_code="",
            business_place="",
            period_type=period_type,
            year=year,
            month=month,
            quarter=quarter,
        )

        return result_path

    # ==========================================================
    # HKD
    # ==========================================================
    if report_type == ReportType.HKD_INCOME:
        print("➡ HKD_INCOME EXPORT")

        exporter = HKDIncomeSheetExportPDF(
            file_path=file_path,
            user=user,
        )

        return exporter.export(
            period_type=period_type,
            year=year,
            month=month,
            quarter=quarter,
        )

    if report_type == ReportType.HKD_EXPENSE:

        exporter = HKDExpenseSheetExportPDF(
            file_path=file_path,
            user=user,
        )

        return exporter.export(
            period_type=period_type,
            year=year,
            month=month,
            quarter=quarter,
        )

    # ==========================================================
    # ENTERPRISE
    # ==========================================================
    if report_type == ReportType.ENTERPRISE_BALANCE:
        print("➡ ENTERPRISE_BALANCE (NOT IMPLEMENTED)")
        raise ValueError("Chưa triển khai ENTERPRISE_BALANCE")

    # ==========================================================
    # NOT SUPPORTED
    # ==========================================================
    raise ValueError(f"Chưa hỗ trợ report_type: {report_type}")


