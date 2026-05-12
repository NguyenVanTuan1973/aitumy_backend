from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime


def to_decimal(val):
    try:
        if val is None or val == "":
            return Decimal("0")
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def round_money(val):
    if not isinstance(val, Decimal):
        val = Decimal(str(val))
    return val.quantize(Decimal("1."), rounding=ROUND_HALF_UP)


def build_s07_dn_register(data_list):

    rows = []
    stt = 1

    # 🔥 SỐ DƯ ĐẦU (có thể lấy DB sau)
    ton = Decimal("0")

    for row in data_list:

        entries = row.get("entries", [])
        if not entries:
            continue

        doc_no = row.get("number")
        date = row.get("create_date")

        desc = (
            row.get("description")
            or row.get("product_name")
            or ""
        )

        for entry in entries:

            amount = to_decimal(entry.get("amount"))

            debit = entry.get("debit")
            credit = entry.get("credit")

            thu = Decimal("0")
            chi = Decimal("0")

            # 🔥 THU: Nợ 111
            if debit and str(debit).startswith("111"):
                thu = amount
                ton += amount

            # 🔥 CHI: Có 111
            elif credit and str(credit).startswith("111"):
                chi = amount
                ton -= amount

            else:
                continue

            rows.append({
                "stt": stt,
                "ngay_ghi": date,
                "ngay_ct": date,
                "so_ct": doc_no,
                "dien_giai": desc,
                "thu": round_money(thu) if thu else "",
                "chi": round_money(chi) if chi else "",
                "ton": round_money(ton),
                "ghi_chu": ""
            })

            stt += 1

    # 🔥 DÒNG TỔNG
    total_thu = sum(
        [to_decimal(r["thu"]) for r in rows if r["thu"]],
        Decimal("0")
    )
    total_chi = sum(
        [to_decimal(r["chi"]) for r in rows if r["chi"]],
        Decimal("0")
    )

    rows.append({
        "stt": "",
        "ngay_ghi": "",
        "ngay_ct": "",
        "so_ct": "",
        "dien_giai": "Cộng cuối kỳ",
        "thu": round_money(total_thu),
        "chi": round_money(total_chi),
        "ton": round_money(ton),
        "ghi_chu": ""
    })

    return {
        "report_name": "SỔ QUỸ TIỀN MẶT (S07-DN)",
        "headers": [
            {"key": "stt", "label": "STT"},
            {"key": "ngay_ghi", "label": "Ngày ghi"},
            {"key": "ngay_ct", "label": "Ngày CT"},
            {"key": "so_ct", "label": "Số CT"},
            {"key": "dien_giai", "label": "Diễn giải"},
            {"key": "thu", "label": "Thu"},
            {"key": "chi", "label": "Chi"},
            {"key": "ton", "label": "Tồn"},
            {"key": "ghi_chu", "label": "Ghi chú"},
        ],
        "rows": rows,
        "generated_at": datetime.now()
    }