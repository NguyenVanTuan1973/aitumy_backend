from collections import defaultdict
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def parse_date(val):
    if not val:
        return ""
    try:
        return datetime.strptime(val, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return val


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


def build_so1_dn_register(data_list):

    if not data_list:
        return {
            "rows": [],
            "total_no": 0,
            "total_co": 0
        }

    # =============================
    # 🔹 1. GROUP THEO CHỨNG TỪ
    # =============================
    vouchers = defaultdict(list)

    for row in data_list:
        key = (
            row.get("number"),
            row.get("create_date"),
            row.get("date"),
            row.get("product_name")
        )
        vouchers[key].append(row)

    # =============================
    # 🔹 2. SORT
    # =============================
    sorted_keys = sorted(
        vouchers.keys(),
        key=lambda x: (x[2] or "", x[1] or "", x[0] or "")
    )

    processed_rows = []
    stt = 1

    total_no = Decimal("0")
    total_co = Decimal("0")

    # =============================
    # 🔹 3. BUILD
    # =============================
    for key in sorted_keys:
        doc_no, create_date, posting_date, desc = key
        rows = vouchers[key]

        first_line = True

        for row in rows:
            entries = row.get("entries", [])
            if not entries:
                continue

            for entry in entries:
                amount = to_number(entry.get("amount"))
                amount = round_money(amount)

                if amount is None:
                    continue

                amount = int(amount)

                debit_acc = entry.get("debit")
                credit_acc = entry.get("credit")

                row_data = {
                    "stt": stt if first_line else "",
                    "date": parse_date(posting_date) if first_line else "",
                    "so_ct": doc_no if first_line else "",
                    "ngay_ct": parse_date(create_date) if first_line else "",
                    "dien_giai": desc if first_line else "",
                    "tk_no": debit_acc,
                    "tk_co": credit_acc,
                    "ps_no": amount,
                    "ps_co": amount
                }

                processed_rows.append(row_data)

                total_no += amount
                total_co += amount

                first_line = False

        # chỉ tăng STT nếu có dòng hợp lệ
        if not first_line:
            stt += 1

    # =============================
    # 🔥 DÒNG TỔNG
    # =============================
    processed_rows.append({
        "stt": "",
        "date": "",
        "so_ct": "",
        "ngay_ct": "",
        "dien_giai": "Cộng số phát sinh",
        "tk_no": "",
        "tk_co": "",
        "ps_no": total_no,
        "ps_co": total_co
    })

    return {
        "report_name": "NHẬT KÝ SỔ CÁI (S01-DN)",
        "rows": processed_rows,
        "generated_at": datetime.now(),
        "total_no": total_no,
        "total_co": total_co,
        "headers": [
            {"key": "stt", "label": "Số TK"},
            {"key": "date", "label": "Ngày ghi"},
            {"key": "so_ct", "label": "Số CT"},
            {"key": "ngay_ct", "label": "Ngày CT"},
            {"key": "dien_giai", "label": "Diễn giải"},
            {"key": "tk_no", "label": "TK Nợ"},
            {"key": "tk_co", "label": "TK Có"},
            {"key": "ps_no", "label": "PS Nợ"},
            {"key": "ps_co", "label": "PS Có"},
        ],
    }