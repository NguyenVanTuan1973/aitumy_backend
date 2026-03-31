from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime, date

from ..base_register import BaseRegister


class S2cRegister(BaseRegister):

    title = "SỔ CHI TIẾT DOANH THU, CHI PHÍ"
    form_code = "S2c-HKD"

    # ==========================
    # Filter rows
    # ==========================

    def filter_rows(self, rows):
        # S2c hiển thị cả income + expense
        return rows

    # ==========================
    # Build PDF
    # ==========================

    def build_pdf(self, renderer, organization, rows, year):

        styles = renderer.styles

        elements = []

        # ==========================
        # HEADER (2 columns)
        # ==========================

        left_header = [

            Paragraph(
                f"Hộ, cá nhân: <b>{organization.name}</b>",
                styles["Normal"]
            ),

            Paragraph(
                f"Địa chỉ: {organization.address}",
                styles["Normal"]
            ),
        ]

        right_header = [

            Paragraph(
                f"<b>Mẫu số {self.form_code}</b>",
                styles["PDFRight"]
            ),

            Paragraph(
                "(Kèm theo Thông tư 152/2025/TT-BTC)",
                styles["PDFRight"]
            ),
        ]

        header_table = Table(
            [[left_header, right_header]],
            colWidths=[270, 270]
        )

        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))

        elements.append(header_table)

        elements.append(Spacer(1, 10))

        # ==========================
        # TITLE
        # ==========================

        elements.append(
            Paragraph(
                f"<b>{self.title}</b>",
                styles["PDFTitle"]
            )
        )

        elements.append(Spacer(1, 10))

        # ==========================
        # META
        # ==========================

        elements.append(
            Paragraph(
                f"Địa điểm kinh doanh: {organization.address}",
                styles["Normal"]
            )
        )

        elements.append(
            Paragraph(
                f"Kỳ kê khai: {year}",
                styles["Normal"]
            )
        )

        elements.append(Spacer(1, 15))

        # ==========================
        # TABLE
        # ==========================

        table_data = [
            ["Diễn giải", "Số tiền"]
        ]

        for r in rows:

            amount = float(r.get("total_amount", 0))

            description = r.get("doc_content") or ""

            table_data.append([
                description,
                f"{amount:,.0f}"
            ])

        table = Table(
            table_data,
            colWidths=[400, 140],
            repeatRows=1
        )

        table.setStyle(TableStyle([

            ("GRID", (0,0), (-1,-1), 0.5, colors.black),

            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),

            ("ALIGN", (1,1), (1,-1), "RIGHT"),

            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),

        ]))

        elements.append(table)

        elements.append(Spacer(1, 25))

        # ==========================
        # SIGNATURE
        # ==========================

        today = datetime.today()

        signature_content = [

            Paragraph(
                f"Ngày {today.day} tháng {today.month} năm {today.year}",
                styles["PDFRight"]
            ),

            Spacer(1, 10),

            Paragraph(
                "<b>NGƯỜI ĐẠI DIỆN HỘ KINH DOANH</b>",
                styles["PDFCenter"]
            ),

            Paragraph(
                "CÁ NHÂN KINH DOANH",
                styles["PDFCenter"]
            ),

            Paragraph(
                "(Ký, ghi rõ họ tên, đóng dấu nếu có)",
                styles["PDFCenter"]
            ),

            # Spacer(1, 50),
            #
            # Paragraph(
            #     f"<b>{organization.owner}</b>",
            #     styles["PDFCenter"]
            # ),
        ]

        signature_table = Table(
            [["", signature_content]],
            colWidths=[270, 270]
        )

        signature_table.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))

        elements.append(signature_table)

        return elements