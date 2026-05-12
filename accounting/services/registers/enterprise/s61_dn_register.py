from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def to_number(val):
    try:
        if val is None or val == "":
            return None
        return Decimal(str(val))  # 🔥 bắt buộc str()
    except (InvalidOperation, ValueError):
        return None

def round_money(val):
    if val is None:
        return None
    if not isinstance(val, Decimal):
        val = Decimal(str(val))  # 🔥 ép về Decimal nếu lỡ sót
    return val.quantize(Decimal("1."), rounding=ROUND_HALF_UP)


def build_s61_dn_register(data_list):
    """
    Build Sổ theo dõi thuế GTGT (S61-DN)
    """

    processed_rows = []
    stt = 1

    for row in data_list:
        entries = row.get("entries", [])
        if not entries:
            continue

        doc_no = row.get("number") or "CT"
        date = row.get("create_date")

        desc = (
            row.get("product_name")
            or row.get("description")
            or "Hạch toán"
        )

        first_line = True

        for entry in entries:
            amount = to_number(entry.get("amount"))
            amount = round_money(amount)

            if amount is None:
                continue

            debit_acc = entry.get("debit")
            credit_acc = entry.get("credit")

            # 🔥 CHỈ LẤY CÁC TK THUẾ (133, 3331...)
            if not (
                (debit_acc and str(debit_acc).startswith("133")) or
                (credit_acc and str(credit_acc).startswith("3331"))
            ):
                continue

            row_data = {
                "stt": stt if first_line else "",
                "so_ct": doc_no if first_line else "",
                "ngay_ct": date if first_line else "",
                "dien_giai": desc if first_line else "",
                "tai_khoan": debit_acc or credit_acc,
                "ps_no": amount if debit_acc else "",
                "ps_co": amount if credit_acc else ""
            }

            processed_rows.append(row_data)
            first_line = False

        # chỉ tăng STT nếu có dòng hợp lệ
        if not first_line:
            stt += 1

    # =============================
    # 🔥 TÍNH TỔNG
    # =============================
    total_no = Decimal("0")
    total_co = Decimal("0")

    for r in processed_rows:
        if r.get("ps_no"):
            total_no += Decimal(str(r["ps_no"]))
        if r.get("ps_co"):
            total_co += Decimal(str(r["ps_co"]))

    processed_rows.append({
        "stt": "",
        "so_ct": "",
        "ngay_ct": "",
        "dien_giai": "Cộng số phát sinh",
        "tai_khoan": "",
        "ps_no": total_no,
        "ps_co": total_co
    })

    return {
        "report_name": "SỔ THEO DÕI THUẾ GTGT (S61-DN)",
        "rows": processed_rows,
        "generated_at": datetime.now()
    }