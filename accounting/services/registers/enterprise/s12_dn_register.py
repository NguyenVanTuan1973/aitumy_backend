from decimal import Decimal, InvalidOperation
from datetime import datetime


def to_decimal(val):
    try:
        if val is None or val == "":
            return Decimal("0")
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def build_s12_dn_register(data_list, product_filter=None):

    rows = []
    stt = 1

    current_qty = Decimal("0")

    for row in data_list:

        product = row.get("product_name")

        # 🔥 Lọc theo sản phẩm (quan trọng cho Thẻ kho)
        if product_filter and product != product_filter:
            continue

        entries = row.get("entries", [])
        if not entries:
            continue

        doc_no = row.get("number")
        date = row.get("create_date")

        desc = (
            row.get("product_name")
            or row.get("description")
            or ""
        )

        for entry in entries:

            qty = to_decimal(entry.get("quantity"))
            if qty == 0:
                continue

            debit = entry.get("debit")
            credit = entry.get("credit")

            nhap = Decimal("0")
            xuat = Decimal("0")

            # Nhập kho
            if debit and str(debit).startswith(("152", "156")):
                nhap = qty
                current_qty += qty

            # Xuất kho
            elif credit and str(credit).startswith(("152", "156")):
                xuat = qty
                current_qty -= qty

            else:
                continue

            rows.append({
                "stt": stt,
                "ngay": date,
                "so_ct": doc_no,
                "dien_giai": desc,
                "ngay_nhap_xuat": date,
                "nhap": nhap,
                "xuat": xuat,
                "ton": current_qty,
                "ky_nhan": ""
            })

            stt += 1

    # 🔥 dòng cộng
    rows.append({
        "stt": "",
        "ngay": "",
        "so_ct": "",
        "dien_giai": "Cộng cuối kỳ",
        "ngay_nhap_xuat": "",
        "nhap": "",
        "xuat": "",
        "ton": current_qty,
        "ky_nhan": ""
    })

    return {
        "report_name": "THẺ KHO (S12-DN)",
        "rows": rows,
        "generated_at": datetime.now(),
        "headers": [
            {"key": "stt", "label": "STT"},
            {"key": "ngay", "label": "Ngày CT"},
            {"key": "so_ct", "label": "Số CT"},
            {"key": "dien_giai", "label": "Diễn giải"},
            {"key": "ngay_nhap_xuat", "label": "Ngày N/X"},
            {"key": "nhap", "label": "SL Nhập"},
            {"key": "xuat", "label": "SL Xuất"},
            {"key": "ton", "label": "SL Tồn"},
            {"key": "ky_nhan", "label": "Ký nhận"},
        ],
    }