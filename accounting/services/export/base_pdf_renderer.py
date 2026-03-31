import os

from django.conf import settings

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table
)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from reportlab.platypus.tables import TableStyle
from reportlab.lib import colors

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ==========================================================
# FONT CONFIG
# ==========================================================

FONT_NAME = "DejaVu"

font_path = os.path.join(
    settings.BASE_DIR,
    "static",
    "fonts",
    "DejaVuSans.ttf"
)

if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
    pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))


# ==========================================================
# BASE PDF RENDERER
# ==========================================================

class BasePDFRenderer:

    FONT_NAME = FONT_NAME

    def __init__(self, file_path):

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        self.file_path = file_path

        # ===============================
        # PDF DOCUMENT
        # ===============================

        self.doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm
        )

        # ===============================
        # STYLES
        # ===============================

        self.styles = getSampleStyleSheet()

        # ép toàn bộ stylesheet dùng DejaVu
        for style in self.styles.byName.values():
            style.fontName = self.FONT_NAME

        self.styles["Normal"].fontSize = 10
        self.styles["Normal"].leading = 14

        # title
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

        # center
        if "PDFCenter" not in self.styles:
            self.styles.add(ParagraphStyle(
                name="PDFCenter",
                fontName=self.FONT_NAME,
                alignment=TA_CENTER,
                fontSize=11,
                leading=15,
                spaceAfter=6,
            ))

        # right
        if "PDFRight" not in self.styles:
            self.styles.add(ParagraphStyle(
                name="PDFRight",
                fontName=self.FONT_NAME,
                alignment=TA_RIGHT,
                fontSize=10,
                leading=14,
            ))

    # ==========================================================
    # FIX TABLE FONT
    # ==========================================================

    def _fix_table_font(self, element):

        if isinstance(element, Table):

            element.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), self.FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))

        return element

    # ==========================================================
    # AUTO FIX TEXT
    # ==========================================================

    def _fix_text(self, element):

        # nếu là string -> convert thành Paragraph
        if isinstance(element, str):

            return Paragraph(
                element,
                self.styles["Normal"]
            )

        return element

    # ==========================================================
    # BUILD PDF
    # ==========================================================

    def build(self, elements):

        fixed_elements = []

        for el in elements:

            el = self._fix_text(el)
            el = self._fix_table_font(el)

            fixed_elements.append(el)

        self.doc.build(fixed_elements)

        return self.file_path