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


def build_s06_dn_register(data_list):

    account_map = {}

    # =============================
    # 🔥 GOM THEO TÀI KHOẢN
    # =============================
    for row in data_list:

        entries = row.get("entries", [])
        for entry in entries:

            amount = to_decimal(entry.get("amount"))

            debit = entry.get("debit")
            credit = entry.get("credit")

            # NỢ
            if debit:
                acc = str(debit)
                if acc not in account_map:
                    account_map[acc] = {
                        "no": Decimal("0"),
                        "co": Decimal("0")
                    }
                account_map[acc]["no"] += amount

            # CÓ
            if credit:
                acc = str(credit)
                if acc not in account_map:
                    account_map[acc] = {
                        "no": Decimal("0"),
                        "co": Decimal("0")
                    }
                account_map[acc]["co"] += amount

    # =============================
    # 🔥 BUILD ROWS
    # =============================
    rows = []
    total = {
        "open_no": Decimal("0"),
        "open_co": Decimal("0"),
        "ps_no": Decimal("0"),
        "ps_co": Decimal("0"),
        "end_no": Decimal("0"),
        "end_co": Decimal("0"),
    }

    for acc, val in sorted(account_map.items()):

        open_no = Decimal("0")
        open_co = Decimal("0")

        ps_no = val["no"]
        ps_co = val["co"]

        # 🔥 TÍNH DƯ CUỐI
        balance = ps_no - ps_co

        if balance >= 0:
            end_no = balance
            end_co = Decimal("0")
        else:
            end_no = Decimal("0")
            end_co = -balance

        rows.append({
            "account": acc,
            "name": "",  # bạn có thể map tên TK sau
            "open_no": round_money(open_no),
            "open_co": round_money(open_co),
            "ps_no": round_money(ps_no),
            "ps_co": round_money(ps_co),
            "end_no": round_money(end_no),
            "end_co": round_money(end_co),
        })

        # cộng tổng
        total["ps_no"] += ps_no
        total["ps_co"] += ps_co
        total["end_no"] += end_no
        total["end_co"] += end_co

    # =============================
    # 🔥 DÒNG TỔNG
    # =============================
    rows.append({
        "account": "",
        "name": "Tổng cộng",
        "open_no": "",
        "open_co": "",
        "ps_no": round_money(total["ps_no"]),
        "ps_co": round_money(total["ps_co"]),
        "end_no": round_money(total["end_no"]),
        "end_co": round_money(total["end_co"]),
    })

    return {
        "report_name": "BẢNG CÂN ĐỐI SỐ PHÁT SINH (S06-DN)",
        "rows": rows,
        "generated_at": datetime.now(),
        "headers": [
            {"key": "account", "label": "Số TK"},
            {"key": "name", "label": "Tên tài khoản"},
            {"key": "open_no", "label": "Nợ đầu kỳ"},
            {"key": "open_co", "label": "Có đầu kỳ"},
            {"key": "ps_no", "label": "Nợ trong kỳ"},
            {"key": "ps_co", "label": "Có trong kỳ"},
            {"key": "end_no", "label": "Nợ cuối kỳ"},
            {"key": "end_co", "label": "Có cuối kỳ"},
        ],
    }