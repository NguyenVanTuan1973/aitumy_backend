import os
from datetime import datetime

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table,
    TableStyle,
    Spacer,
)
from reportlab.pdfbase import pdfmetrics



FONT_NAME = "DejaVu"

font_path = os.path.join(
    settings.BASE_DIR,
    "static",
    "fonts",
    "DejaVuSans.ttf"
)

if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
    pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))


class BasePDFRenderer:
    """
    Renderer PDF dùng chung cho các mẫu sổ HKD
    (Tuân thủ TT 88/2021/TT-BTC – hỗ trợ Unicode tiếng Việt)
    """

    FONT_NAME = "DejaVu"

    def __init__(self, file_path: str):

        # ===== 1. Đảm bảo folder backend tồn tại =====
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        self.file_path = file_path

        # ===== 3. Styles =====
        self.styles = getSampleStyleSheet()

        self.styles["Normal"].fontName = self.FONT_NAME
        self.styles["Normal"].fontSize = 10
        self.styles["Normal"].leading = 14

        if "PDFTitle" not in self.styles:
            self.styles.add(ParagraphStyle(
                name="PDFTitle",
                fontName=self.FONT_NAME,
                alignment=TA_CENTER,
                fontSize=14,
                leading=18,
                spaceAfter=12,
                spaceBefore=6,
            ))

        if "PDFCenter" not in self.styles:
            self.styles.add(ParagraphStyle(
                name="PDFCenter",
                fontName=self.FONT_NAME,
                alignment=TA_CENTER,
                fontSize=11,
                leading=15,
                spaceAfter=6,
            ))

        if "PDFRight" not in self.styles:
            self.styles.add(ParagraphStyle(
                name="PDFRight",
                fontName=self.FONT_NAME,
                alignment=TA_RIGHT,
                fontSize=10,
                leading=14,
            ))

        self.story: list = []

    # ==========================================================
    # HEADER – PHÁP LÝ
    # ==========================================================

    def build_header(
        self,
        ho_ten: str,
        dia_chi: str,
        ma_so_thue: str,
        mau_so: str,
        thong_tu: str,
    ):
        self.story.extend([
            Paragraph(f"Hộ, cá nhân kinh doanh: {ho_ten}", self.styles["Normal"]),
            Paragraph(f"Địa chỉ: {dia_chi}", self.styles["Normal"]),
            Paragraph(f"Mã số thuế: {ma_so_thue}", self.styles["Normal"]),
            Spacer(1, 6 * mm),
        ])

    # ==========================================================
    # TITLE
    # ==========================================================

    def build_title(
        self,
        title: str,
        dia_diem_kinh_doanh: str,
        ky_ke_khai: str,
    ):
        self.story.extend([
            Paragraph(title, self.styles["PDFTitle"]),
            Paragraph(f"Địa điểm kinh doanh: {dia_diem_kinh_doanh}", self.styles["Normal"]),
            Paragraph(f"Kỳ kê khai: {ky_ke_khai}", self.styles["Normal"]),
            Spacer(1, 8 * mm),
        ])
    # ==========================================================
    # TABLE
    # ==========================================================

    def build_table(self, rows: list):
        """
        rows = [
            ["Ngày tháng", "Diễn giải", "Số tiền"],
            ["2026-01-01", "Bán hàng", "3.500.000"],
            ...
        ]
        """

        table = Table(
            rows,
            colWidths=[30 * mm, 110 * mm, 35 * mm],
            repeatRows=1,
        )

        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), self.FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
        ]))

        self.story.extend([
            table,
            Spacer(1, 6 * mm),
        ])

    # ==========================================================
    # TOTAL
    # ==========================================================

    def build_total(self, total_amount: str):
        self.story.extend([
            Paragraph(f"<b>Tổng cộng:</b> {total_amount}", self.styles["Normal"]),
            Spacer(1, 10 * mm),
        ])

    # ==========================================================
    # SIGNATURE
    # ==========================================================

    def build_signature(self):
        today = datetime.today()

        self.story.extend([
            Paragraph(
                f"Ngày {today.day} tháng {today.month} năm {today.year}",
                self.styles["PDFRight"],
            ),
            Spacer(1, 15 * mm),
            Paragraph(
                "NGƯỜI ĐẠI DIỆN HỘ KINH DOANH<br/>"
                "CÁ NHÂN KINH DOANH<br/>"
                "(Ký, ghi rõ họ tên, đóng dấu nếu có)",
                self.styles["PDFCenter"],
            ),
        ])

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(self) -> str:
        """
        Build PDF và trả về đường dẫn file
        """

        doc = SimpleDocTemplate(
            self.file_path,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        doc.build(self.story)
        return self.file_path
