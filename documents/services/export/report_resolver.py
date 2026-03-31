from users.models import Organization
from .report_type import ReportType


class ReportResolverService:

    @staticmethod
    def resolve(report_type: str, organization: Organization, year: int):
        """
        Trả về:
        - file_name
        - sheet_name
        """

        if organization.legal_form == Organization.LegalForm.INDIVIDUAL:

            file_name = f"so_thu_chi_hkd_{year}"

            if report_type == ReportType.INDIVIDUAL_INCOME:
                return file_name, "so_doanh_thu"

            if report_type == ReportType.INDIVIDUAL_EXPENSE:
                return file_name, "so_chi_phi"

            raise ValueError("Report không hợp lệ cho INDIVIDUAL")

        # ===== HKD (mở rộng sau) =====
        if organization.legal_form == Organization.LegalForm.HKD:
            raise ValueError("Chưa hỗ trợ HKD")

        # ===== ENTERPRISE (mở rộng sau) =====
        if organization.legal_form == Organization.LegalForm.ENTERPRISE:
            raise ValueError("Chưa hỗ trợ ENTERPRISE")

        raise ValueError("LegalForm không được hỗ trợ")