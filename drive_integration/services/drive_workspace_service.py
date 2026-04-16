
from users.models import UserDrive, DriveFolder
from django.utils import timezone
from users.models import UserDrive, DriveFolder
from drive_integration.google_client import GoogleDriveClient

from .google_oauth_service import GoogleOAuthService

ROOT_FOLDER_NAME = "Ttumy_Accounting"


class DriveWorkspaceService:

    def ensure(self, user, organization=None):

        current_year = timezone.now().year

        drive = UserDrive.objects.filter(user=user).first()
        if not drive:
            raise Exception("Google Drive not connected")

        # ✅ LẤY TOKEN CHUẨN (AUTO REFRESH)
        credentials = GoogleOAuthService.get_credentials_for_user(user=user)

        # ✅ DÙNG TOKEN MỚI
        client = GoogleDriveClient(credentials.token)


        root_folder = self._ensure_root_folder(drive, client)

        year_folder = self._ensure_year_folder(
            drive,
            client,
            root_folder,
            current_year
        )

        sheet_node = self._ensure_year_spreadsheet(
            drive,
            client,
            year_folder,
            current_year
        )

        chung_tu_folder = self._ensure_chung_tu_folder(
            drive,
            client,
            year_folder
        )

        self._ensure_month_folders(
            drive,
            client,
            chung_tu_folder
        )

        return {
            "sheet": {
                "spreadsheet_id": sheet_node.sheet_id
            }
        }

    # ======================================================
    # ROOT
    # ======================================================

    def _ensure_root_folder(self, drive, client):

        node = DriveFolder.objects.filter(
            drive=drive,
            name=ROOT_FOLDER_NAME,
            node_type="folder",
            parent_folder=None
        ).first()

        if node:
            return node

        folder_id = client.create_folder(ROOT_FOLDER_NAME)

        return DriveFolder.objects.create(
            drive=drive,
            name=ROOT_FOLDER_NAME,
            node_type="folder",
            folder_id=folder_id,
            parent_folder=None,
        )

    # ======================================================
    # YEAR
    # ======================================================

    def _ensure_year_folder(self, drive, client, root_folder, year):

        year_name = str(year)

        node = DriveFolder.objects.filter(
            drive=drive,
            name=year_name,
            node_type="folder",
            parent_folder=root_folder
        ).first()

        if node:
            return node

        folder_id = client.create_folder(
            year_name,
            parent_id=root_folder.folder_id
        )

        return DriveFolder.objects.create(
            drive=drive,
            name=year_name,
            node_type="folder",
            folder_id=folder_id,
            parent_folder=root_folder,
        )

    # ======================================================
    # SPREADSHEET
    # ======================================================

    def _ensure_year_spreadsheet(self, drive, client, year_folder, year):

        sheet_name = f"HKD_DATA_{year}"

        node = DriveFolder.objects.filter(
            drive=drive,
            name=sheet_name,
            node_type="sheet",
            parent_folder=year_folder
        ).first()

        if node:
            return node

        # 🟢 1. Tạo spreadsheet
        spreadsheet_id = client.create_sheet(
            sheet_name,
            parent_id=year_folder.folder_id
        )

        # 🟢 2. Tạo các tab chuẩn
        client.add_sheets(
            spreadsheet_id,
            [
                "opening_balances",         # Số dư đầu kỳ (111, 112, 131, 331)
                "document_set",             # Bộ chứng từ
                "documents_metadata",       # Dữ liệu chứng từ
                "data_source",              # Sổ nhật ký chứng từ
                "inventory_opening",        # Hàng tồn kho/ danh sách SP HH
                "customer_list",            # Khách hàng
                "supplier_list",            # Nhà cung cấp
                "employee_list",            # Nhân viên
                "bank_list",                # Ngân hàng
                "warehouse_list",           # Kho hàng
            ]
        )

        # ==========================
        # OPENING BALANCES HEADER
        # ==========================
        client.write_row(
            spreadsheet_id,
            "opening_balances",     # BẢNG SỐ DƯ ĐÀU KỲ TÀI KHOẢN
            [
                "account_number",           # Số tài khoản
                "sub_account_number",        # Chi tiết tài khản
                "debt_amount",              # PS Nợ
                "credit_amount",             # PS Có
                "created_at",
            ]
        )

        client.write_row(
            spreadsheet_id,
            "document_set",
            [
                "set_id",  # ID bộ chứng từ (SET20260312A1)
                "set_name",  # Tên bộ chứng từ (Mua hàng Bia Tiger)
                "doc_date",  # Ngày nghiệp vụ chính
                "doc_content",  # Nội dung
                "total_amount",  # Tổng tiền
                "document_count",  # Số chứng từ trong bộ
                "drive_folder_id", # folder trên Google Drive
                "status",  # draft / posted / archived
                "created_at",
                "updated_at",
            ]
        )

        client.write_row(
            spreadsheet_id,
            "documents_metadata",
            [
                "doc_id",            # Mã chứng từ duy nhất (DOC_2026_000001)
                "doc_symbol",        # Ký hiệu mẫu (1C25TNM, 01GTKT...)
                "doc_type",          # Loại CT (PT, PC, HD_BAN, HD_MUA...)
                "doc_number",        # Số chứng từ
                "doc_date",          # Ngày chứng từ
                "doc_content",       # Nội dung chứng từ
                "period",            # Tháng (01-12)
                "tax_amount",        # Tiền thuế
                "total_amount",      # Tổng tiền
                "discount_amount",   # Tiền giảm giá
                "tax_rate",          # Thuế suất %
                "payment_type",      # Cash / Bank / Debt
                "repayment_day",     # Ngày trả nợ nếu debt
                "out_in_code",       # Mã xuất / nhập
                "industry_code",     # Mã ngành nghề HKD
                "doc_register",      # Sổ ghi (S1a-HKD, S2a-HKD...)
                "file_drive_id",     # ID file Google Drive
                "file_name",         # Tên file upload
                "mime_type",         # application/pdf, image/jpeg
                "file_size",         # kích thước file (bytes)
                "folder_month",      # Tháng lưu trên Drive (01-12)
                "job_code",          # Danh mục nghiệp vụ
                "object_code",       # customer / supplier / employee
                "accounting_code",   # Mã hạch toán
                "set_id",            # Bộ chứng từ
                "status",            # draft / posted / deleted
                "created_at",
                "updated_at",
            ]
        )

        # 🟢 3. Ghi header cho data_source
        client.write_row(
            spreadsheet_id,
            "data_source",      # Sổ nhật ký chứng từ
            [
                "doc_date",                 # Ngày chứng từ
                "doc_number",               # Số chưng từ
                "doc_content",              # Nội dung
                "unit",                     # đơn vị
                "quantity",                 # số lượng
                "price",                    # đơn giá
                "total_amount",             # số tiền
                "tax_vat_amount",           # tiền thuế GTGT
                "tax_individual_amount",    # tiền thuế TNCN
                "special_tax_amount",       # Mức thuế tuyệt đối (xuất khẩu, nhập khẩu, TTDB)
                "tax_price_per_unit",       # Giá tính thuế/1 đơn vị sản phẩm
                "tax_rate",                 # Thuế suất
                "discount_amount",          # Giảm giá hàng bán
                "payment_type",             # Hình thức thanh toán (Cash, Bank, debt)
                "repayment_date",            # Ngày trả nợ (nếu là debt)
                "out_in_code",              # Mã xuất, nhập N/X
                "product_code",             # Mã sản phẩm
                "job_code",                 # Mã danh mục (Bán hàng/Thu khác/Mua hàng, chi khác ...)
                "industry_code",            # Mã ngành nghề (app)
                "customer_code",            # Mã khách hàng
                "supplier_code",            # Mã nhà cung cấp
                "employee_code",            # Mã nhân viên
                "bank_code",                # Mã ngân hàng
                "doc_register",             # Ghi vào sổ (S1a-HKD, S2a-HKD, S2b-HKD, S2c-HKD, S2d-HKD, S2e-HKD)
                "accounting_code",          # Mã hạch toán Nợ/Có (N12C20, C11N25, ...)
                "metadata_code",            # documents_metadata.doc_id
                "set_id",                   # Bộ chứng từ
                "created_at",
            ]
        )

        client.write_row(
            spreadsheet_id,
            "inventory_opening",
            [
                "product_code",             # Mã SP
                "product_name",             # Tên SP
                "unit",                     # Đơn vị tính
                "opening_quantity",         # Số lượng đầu kỳ
                "opening_amount",           # Giá trị đầu kỳ
                "warehouse_code",           # Mã kho
                "created_at",
            ]
        )

        client.write_row(
            spreadsheet_id,
            "customer_list",
            [
                "customer_code",            # Mã
                "customer_name",            # Tên
                "customer_address",         # Địa chỉ
                "customer_tax_number",      # Mã số thuế
                "customer_phone",           # Điẹn thoại
                "customer_email",           # Email
                "customer_debt",            # Nợ đầu kỳ
                "customer_credit",          # có đầu kỳ
                "created_at",
            ]
        )

        client.write_row(
            spreadsheet_id,
            "supplier_list",
            [
                "supplier_code",             # Mã
                "supplier_name",            # Tên
                "supplier_address",         # Địa chỉ
                "supplier_tax_number",      # Mã số thuế
                "supplier_phone",           # Điẹn thoại
                "supplier_email",           # Email
                "supplier_debt",            # Nợ đầu kỳ
                "supplier_credit",          # có đầu kỳ
                "created_at",
            ]
        )

        client.write_row(
            spreadsheet_id,
            "employee_list",
            [
                "employee_code",            # Mã
                "employee_name",            # Tên
                "employee_address",         # Địa chỉ
                "employee_tax_number",      # Mã số thuế
                "employee_phone",           # Điẹn thoại
                "employee_email",           # Email
                "employee_debt",            # Nợ đầu kỳ
                "employee_credit",          # có đầu kỳ
                "created_at",
            ]
        )

        client.write_row(
            spreadsheet_id,
            "bank_list",
            [
                "bank_code",                # Mã
                "bank_name",                # Tên
                "bank_address",             # Địa chỉ
                "bank_tax_number",          # Mã số thuế
                "bank_phone",               # Điẹn thoại
                "bank_email",               # Email
                "bank_debt",                # Nợ đầu kỳ
                "bank_credit",              # có đầu kỳ
                "created_at",
            ]
        )

        client.write_row(
            spreadsheet_id,
            "warehouse_list",
            [
                "warehouse_code",           # Mã
                "warehouse_name",           # Tên
                "warehouse_address",        # Địa chỉ
                "warehouse_phone",          # Điẹn thoại
                "warehouse_email",          # Email
                "warehouse_debt",           # Nợ đầu kỳ
                "warehouse_credit",         # có đầu kỳ
                "created_at",
            ]
        )

        return DriveFolder.objects.create(
            drive=drive,
            name=sheet_name,
            node_type="sheet",
            sheet_id=spreadsheet_id,
            parent_folder=year_folder,
        )

    # ======================================================
    # CHUNG_TU
    # ======================================================

    def _ensure_chung_tu_folder(self, drive, client, year_folder):

        node = DriveFolder.objects.filter(
            drive=drive,
            name="CHUNG_TU",
            node_type="folder",
            parent_folder=year_folder
        ).first()

        if node:
            return node

        folder_id = client.create_folder(
            "CHUNG_TU",
            parent_id=year_folder.folder_id
        )

        return DriveFolder.objects.create(
            drive=drive,
            name="CHUNG_TU",
            node_type="folder",
            folder_id=folder_id,
            parent_folder=year_folder,
        )

    # ======================================================
    # MONTH
    # ======================================================

    def _ensure_month_folders(self, drive, client, chung_tu_folder):

        for month in range(1, 13):

            month_name = f"{month:02d}"

            exists = DriveFolder.objects.filter(
                drive=drive,
                name=month_name,
                node_type="folder",
                parent_folder=chung_tu_folder
            ).exists()

            if not exists:

                folder_id = client.create_folder(
                    month_name,
                    parent_id=chung_tu_folder.folder_id
                )

                DriveFolder.objects.create(
                    drive=drive,
                    name=month_name,
                    node_type="folder",
                    folder_id=folder_id,
                    parent_folder=chung_tu_folder,
                )