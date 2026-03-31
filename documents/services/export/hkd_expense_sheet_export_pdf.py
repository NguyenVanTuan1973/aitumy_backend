import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from users.models import UserDrive, DriveFolder
from drive_integration.utils.period_utils import get_period_range

from drive_integration.views import parse_sheet_date
from .base_pdf_renderer import BasePDFRenderer


class HKDExpenseSheetExportPDF:
    """
    Export PDF Sổ chi phí HKD
    - Dữ liệu THẬT từ Google Sheet
    """

    def __init__(self, file_path: str, user):
        self.file_path = file_path
        self.user = user

    # =====================================================
    # PUBLIC
    # =====================================================

    def export(
        self,
        owner_name: str,
        address: str,
        tax_code: str,
        business_place: str,
        period_type: str,
        year: int,
        month: int | None = None,
        quarter: int | None = None,
    ) -> str:

        print("Chạy qua def export")

        # =========================
        # 1. RESOLVE PERIOD
        # =========================
        period_label, start_date, end_date = self._resolve_period(
            period_type, year, month, quarter
        )
        # =========================
        # 2. LOAD DATA FROM SHEET
        # =========================
        transactions, total = self._load_expense_from_sheet(
            start_date, end_date
        )

        # =========================
        # 3. INIT RENDERER (🔥 BẮT BUỘC)
        # =========================
        renderer = BasePDFRenderer(self.file_path)

        print("renderer :", renderer)

        # ----- HEADER PHÁP LÝ -----
        renderer.build_header(
            ho_ten=owner_name,
            dia_chi=address,
            ma_so_thue=tax_code,
            mau_so="S1a-HKD",
            thong_tu="Thông tư 152/2025/TT-BTC",
        )

        # ----- TITLE -----
        renderer.build_title(
            title="SỔ CHI PHÍ HOẠT ĐỘNG KINH DOANH",
            dia_diem_kinh_doanh=business_place,
            ky_ke_khai=period_label,
        )

        # ----- TABLE -----
        rows = [["Ngày", "Diễn giải", "Số tiền"]]
        total_amount = 0

        for t in transactions:
            rows.append([
                t["date"],
                t["description"],
                f"{int(t['amount']):,}".replace(",", "."),
            ])

        renderer.build_table(rows)

        # ----- TOTAL -----
        renderer.build_total(
            f"{int(total_amount):,}".replace(",", ".")
        )

        # ----- SIGNATURE -----
        renderer.build_signature()

        return renderer.render()

    # =====================================================
    # INTERNAL
    # =====================================================

    def _debug_resolve_period(self, period_type, year, month, quarter):
        print("===== DEBUG _resolve_period =====")
        print("period_type =", period_type, type(period_type))
        print("year        =", year, type(year))
        print("month       =", month, type(month))
        print("quarter     =", quarter, type(quarter))

        try:
            result = self._resolve_period(period_type, year, month, quarter)
            print("RETURN VALUE =", result)
            print("label       =", result[0], type(result[0]))
            print("start_date  =", result[1], type(result[1]))
            print("end_date    =", result[2], type(result[2]))
            print("===== DEBUG OK =====")
            return result

        except Exception as e:
            print("❌ DEBUG ERROR in _resolve_period:", repr(e))
            raise

    def _debug_load_expense_from_sheet(self, start_date, end_date):
        print("===== DEBUG _load_expense_from_sheet =====")
        print("start_date =", start_date, type(start_date))
        print("end_date   =", end_date, type(end_date))
        print("user       =", self.user)

        try:
            result = self._load_expense_from_sheet(start_date, end_date)
            print("RETURN TYPE =", type(result))
            print("TOTAL ITEMS =", len(result[0]))
            print("TOTAL AMOUNT =", result[1])
            print("===== LOAD SHEET OK =====")
            return result

        except Exception as e:
            print("❌ DEBUG ERROR in _load_expense_from_sheet")
            print("EXCEPTION =", repr(e))
            raise

    def _resolve_period(self, period_type, year, month, quarter):
        if period_type == "month":
            anchor_date = datetime.date(year, int(month), 1)
            label = f"Tháng {month}/{year}"

        elif period_type == "quarter":
            start_month = (int(quarter) - 1) * 3 + 1
            anchor_date = datetime.date(year, start_month, 1)
            label = f"Quý {quarter}/{year}"

        else:
            anchor_date = datetime.date(year, 1, 1)
            label = f"Năm {year}"

        start_date, end_date = get_period_range(period_type, anchor_date)
        return label, start_date, end_date

    def _load_expense_from_sheet(self, start_date, end_date):
        """
        Đọc dữ liệu thật từ sheet 'so_chi_phi'
        """

        # =============================
        # USER DRIVE (GIỐNG PublicSheetAPIView)
        # =============================
        user_drive = UserDrive.objects.filter(user=self.user).first()

        if not user_drive:
            print("⚠️ fallback UserDrive trong export PDF")
            user_drive = UserDrive.objects.first()

        if not user_drive or not user_drive.access_token:
            raise Exception("NO_GOOGLE_DRIVE_CONNECTED")

        # =============================
        # DRIVE FOLDER
        # =============================
        drive_folder = DriveFolder.objects.get(
            drive=user_drive,
            name="so_thu_chi_hkd"
        )

        # =============================
        # GOOGLE SHEETS
        # =============================
        creds = Credentials(
            token=user_drive.access_token,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )

        service = build("sheets", "v4", credentials=creds)

        result = service.spreadsheets().values().get(
            spreadsheetId=drive_folder.folder_id,
            range="so_chi_phi!A:E"
        ).execute()

        rows = result.get("values", [])

        items = []
        total_amount = 0

        for row in rows:
            if len(row) < 3:
                continue

            row_date = parse_sheet_date(row[0])
            if not row_date:
                continue

            if not (start_date <= row_date <= end_date):
                continue

            try:
                amount = float(row[2])
            except Exception:
                continue

            total_amount += amount

            items.append({
                "date": row_date.strftime("%d/%m/%Y"),
                "description": row[1],
                "amount": amount,
            })

        return items, total_amount

