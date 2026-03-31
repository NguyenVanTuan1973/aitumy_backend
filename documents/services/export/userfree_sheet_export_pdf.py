import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .base_pdf_renderer import BasePDFRenderer
from users.models import UserDrive, DriveFolder
from drive_integration.views import parse_sheet_date
from drive_integration.utils.period_utils import get_period_range

from django.conf import settings

class UserFreeSheetExportPDF:
    """
    Export PDF Sổ thu / chi HKD (User Free)
    """

    SHEET_CONFIG = {
        "expense": {
            "sheet_name": "so_chi_phi",
            "title": "SỔ CHI PHÍ HOẠT ĐỘNG KINH DOANH",
        },
        "income": {
            "sheet_name": "so_doanh_thu",
            "title": "SỔ DOANH THU BÁN HÀNG HÓA, DỊCH VỤ",
        },
    }

    def __init__(self, file_path: str, user, sheet_type: str):
        print(">>> RUN __init__ UserFreeSheetExportPDF")
        if sheet_type not in self.SHEET_CONFIG:
            raise ValueError(f"Invalid sheet_type: {sheet_type}")

        self.file_path = file_path
        self.user = user
        self.sheet_type = sheet_type
        self.config = self.SHEET_CONFIG[sheet_type]


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

        print(">>> RUN export()")

        period_label, start_date, end_date = self._resolve_period(
            period_type, year, month, quarter
        )

        transactions, total_amount = self._load_from_sheet(
            start_date, end_date
        )

        renderer = BasePDFRenderer(self.file_path)

        renderer.build_header(
            ho_ten=owner_name,
            dia_chi=address,
            ma_so_thue=tax_code,
            mau_so="S1a-HKD",
            thong_tu="Thông tư 152/2025/TT-BTC",
        )

        renderer.build_title(
            title=self.config["title"],
            dia_diem_kinh_doanh=business_place,
            ky_ke_khai=period_label,
        )

        rows = [["Ngày", "Diễn giải", "Số tiền"]]

        for t in transactions:
            rows.append([
                t["date"],
                t["description"],
                f"{int(t['amount']):,}".replace(",", "."),
            ])

        renderer.build_table(rows)

        renderer.build_total(
            f"{int(total_amount):,}".replace(",", ".")
        )

        renderer.build_signature()

        return renderer.render()

    def _resolve_period(self, period_type, year, month, quarter):
        print("ĐÃ CHẠY _resolve_period")
        if period_type == "month":
            if not month:
                raise ValueError("month is required for period_type=month")

            anchor_date = datetime.date(int(year), int(month), 1)
            label = f"Tháng {month}/{year}"

        elif period_type == "quarter":
            if not quarter:
                raise ValueError("quarter is required for period_type=quarter")

            start_month = (int(quarter) - 1) * 3 + 1
            anchor_date = datetime.date(int(year), start_month, 1)
            label = f"Quý {quarter}/{year}"

        elif period_type == "year":
            anchor_date = datetime.date(int(year), 1, 1)
            label = f"Năm {year}"

        else:
            raise ValueError("Invalid period_type")

        print("ANCHOR DATE:", anchor_date)
        start_date, end_date = get_period_range(period_type, anchor_date)
        print("START:", start_date)
        print("END:", end_date)

        return label, start_date, end_date

    def _load_from_sheet(self, start_date, end_date):
        print("ĐÃ CHẠY _load_from_sheet")

        user_drive = UserDrive.objects.filter(user=self.user).first()

        if not user_drive:
            if settings.DEBUG:
                print("⚠️ DEV MODE: fallback UserDrive")
                user_drive = UserDrive.objects.first()

        if not user_drive or not user_drive.access_token:
            raise Exception("NO_GOOGLE_DRIVE_CONNECTED")

        print("UER_DRIVE:", user_drive)

        if not user_drive or not user_drive.access_token:
            raise Exception("NO_GOOGLE_DRIVE_CONNECTED")

        sheet_folder_name = f"so_thu_chi_hkd_{start_date.year}"

        print("Tìm Google Sheet name:", sheet_folder_name)

        try:
            drive_sheet = DriveFolder.objects.get(
                drive=user_drive,
                name=sheet_folder_name,
                node_type="sheet"
            )
        except DriveFolder.DoesNotExist:
            raise Exception(f"Không tìm thấy Google Sheet {sheet_folder_name}")

        print("NODE TYPE:", drive_sheet.node_type)
        print("SPREADSHEET ID:", drive_sheet.folder_id)

        creds = Credentials(
            token=user_drive.access_token,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )

        service = build("sheets", "v4", credentials=creds)

        sheet_name = self.config["sheet_name"]

        print("sheet_name:", sheet_name)

        result = service.spreadsheets().values().get(
            spreadsheetId=drive_sheet.folder_id,
            range=f"{sheet_name}!A:E"
        ).execute()

        print("=== TẤT CẢ DriveFolder của user ===")
        all_nodes = DriveFolder.objects.filter(drive=user_drive)

        for n in all_nodes:
            print("NAME:", n.name, "| TYPE:", n.node_type)

        rows = result.get("values", [])
        # if rows:
        #     rows = rows[1:]  # bỏ header

        items = []
        total_amount = 0

        for row in rows:
            if len(row) < 3:
                continue

            row_date = parse_sheet_date(row[0])
            if not row_date or not (start_date <= row_date <= end_date):
                continue

            print("RAW ROW:", row)

            try:
                raw_amount = row[2].replace(".", "").replace(",", "")
                amount = float(raw_amount)
            except Exception as e:
                print("AMOUNT PARSE ERROR:", row[2], e)
                continue

            total_amount += amount

            items.append({
                "date": row_date.strftime("%d/%m/%Y"),
                "description": row[1],
                "amount": amount,
            })

        return items, total_amount
