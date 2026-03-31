from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime, date

from ..base_register import BaseRegister

class S2aRegister(BaseRegister):

    title = "SỔ DOANH THU BÁN HÀNG HÓA, DỊCH VỤ"
    form_code = "S2a-HKD"

    # ==========================
    # Filter
    # ==========================

    def filter_rows(self, rows):

        return [
            r for r in rows
            if r.get("job_code") == "income"
        ]

    # ==========================
    # Excel date convert
    # ==========================

    def _excel_date(self, value):
        # Excel number → date
        if isinstance(value, (int, float)):
            try:
                result = datetime.fromordinal(
                    datetime(1900, 1, 1).toordinal() + int(value) - 2
                ).strftime("%d/%m/%Y")

                return result
            except Exception as e:
                print("❌ Error parsing Excel number:", e)

        # datetime
        if isinstance(value, datetime):
            result = value.strftime("%d/%m/%Y")

            return result

        # date
        if isinstance(value, date):
            result = value.strftime("%d/%m/%Y")

            return result

        # string
        if isinstance(value, str):
            value = value.strip()

            formats = [
                "%Y-%m-%dT%H:%M:%S.%f",  # ✅ FIX CHÍNH (case của bạn)
                "%Y-%m-%dT%H:%M:%S",  # có T nhưng không có ms
                "%Y-%m-%d",  # yyyy-mm-dd
                "%d/%m/%Y",
                "%m/%d/%Y",
            ]

            for fmt in formats:
                try:
                    parsed = datetime.strptime(value, fmt)
                    result = parsed.strftime("%d/%m/%Y")

                    return result
                except:
                    continue

            return value

        return value or ""


    def _group_rows(self, rows):

        groups = {}

        for r in rows:

            industry = r.get("industry_code") or 0

            if industry not in groups:
                groups[industry] = []

            groups[industry].append(r)

        return groups

    # ==========================
    # Build PDF layout
    # ==========================

    def build_pdf(self, renderer, organization, rows, year):
        styles = renderer.styles  # ⭐ lấy styles từ renderer
        elements = []

        # ==========================
        # HEADER (2 columns)
        # ==========================

        left_header = Paragraph(
            f"Hộ, cá nhân: <b>{organization.name}</b><br/>"
            f"Địa chỉ: {organization.address}",
            styles["Normal"]
        )


        right_header = Paragraph(
            f"<b>Mẫu số {self.form_code}</b><br/>(Kèm theo Thông tư 152/2025/TT-BTC)",
            styles["PDFRight"]
        )

        header_table = Table(
            [[left_header, right_header]],
            colWidths=[renderer.doc.width / 2, renderer.doc.width / 2]
        )


        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))


        elements.append(header_table)

        elements.append(Spacer(1, 10))

        # TITLE

        elements.append(
            Paragraph(
                f"<b>{self.title}</b>",
                # styles["Title"]
                styles["PDFTitle"]
            )
        )

        elements.append(Spacer(1, 10))

        # META

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

        # GROUP DATA

        groups = self._group_rows(rows)

        total_vat = 0
        total_pit = 0

        index = 1

        for industry, group_rows in groups.items():

            elements.append(
                Paragraph(
                    f"<b>Nhóm ngành {industry}</b>",
                    styles["Normal"]
                )
            )

            elements.append(Spacer(1, 5))

            table_data = [
                ["Số hiệu", "Ngày tháng", "Diễn giải", "Số tiền"]
            ]

            group_total = 0
            vat_total = 0
            pit_total = 0

            for r in group_rows:

                amount = float(r.get("total_amount", 0))

                vat = float(r.get("tax_vat_amount", 0))
                pit = float(r.get("tax_individual_amount", 0))

                group_total += amount
                vat_total += vat
                pit_total += pit

                table_data.append([
                    r.get("doc_number") or "",
                    self._excel_date(r.get("doc_date")),
                    r.get("doc_content") or "",
                    f"{amount:,.0f}"
                ])

            total_width = renderer.doc.width

            table = Table(
                table_data,
                colWidths=[
                    total_width * 0.13,
                    total_width * 0.17,
                    total_width * 0.50,
                    total_width * 0.20,
                ]
            )

            table.setStyle(TableStyle([

                ("GRID", (0,0), (-1,-1), 0.5, colors.black),

                ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),

                ("ALIGN", (3,1), (3,-1), "RIGHT"),

                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),

                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold")

            ]))

            elements.append(table)

            elements.append(Spacer(1, 5))

            elements.append(
                Paragraph(
                    f"Tổng cộng ({index}): {group_total:,.0f}",
                    styles["Normal"]
                )
            )

            elements.append(
                Paragraph(
                    f"Thuế GTGT: {vat_total:,.0f}",
                    styles["Normal"]
                )
            )

            elements.append(
                Paragraph(
                    f"Thuế TNCN: {pit_total:,.0f}",
                    styles["Normal"]
                )
            )

            elements.append(Spacer(1, 15))

            total_vat += vat_total
            total_pit += pit_total

            index += 1

        # TOTAL TAX

        elements.append(
            Paragraph(
                f"<b>Tổng số thuế GTGT phải nộp: {total_vat:,.0f}</b>",
                styles["Normal"]
            )
        )

        elements.append(
            Paragraph(
                f"<b>Tổng số thuế TNCN phải nộp: {total_pit:,.0f}</b>",
                styles["Normal"]
            )
        )

        elements.append(Spacer(1, 10))

        # SIGNATURE
        today = datetime.today()

        signature_content = [
            Paragraph(
                f"Ngày {today.day} tháng {today.month} năm {today.year}",
                styles["PDFCenter"]
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
            [
                ["", signature_content]
            ],
            colWidths=[270, 270]  # chia 2 cột bằng nhau
        )

        signature_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))

        elements.append(signature_table)

        return elements