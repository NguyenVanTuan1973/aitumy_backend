from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime


COST_ACCOUNTS = {
    "621", "622", "623", "627", "154", "631",
    "641", "642", "242", "335", "632"
}


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


def build_s36_dn_register(data_list):

    account_map = {}

    # =============================
    # 🔥 GOM CHI PHÍ
    # =============================
    for row in data_list:

        entries = row.get("entries", [])

        for entry in entries:

            amount = to_decimal(entry.get("amount"))
            debit = entry.get("debit")
            credit = entry.get("credit")

            # =============================
            # CHỈ LẤY TK CHI PHÍ
            # =============================
            if debit and str(debit)[:3] in COST_ACCOUNTS:

                acc = str(debit)

                if acc not in account_map:
                    account_map[acc] = {
                        "no": Decimal("0"),
                        "co": Decimal("0"),
                    }

                account_map[acc]["no"] += amount

            if credit and str(credit)[:3] in COST_ACCOUNTS:

                acc = str(credit)

                if acc not in account_map:
                    account_map[acc] = {
                        "no": Decimal("0"),
                        "co": Decimal("0"),
                    }

                account_map[acc]["co"] += amount

    # =============================
    # 🔥 BUILD ROWS
    # =============================
    rows = []

    total_no = Decimal("0")
    total_co = Decimal("0")

    for acc, val in sorted(account_map.items()):

        no = val["no"]
        co = val["co"]

        rows.append({
            "account": acc,
            "desc": "",

            "total": round_money(no - co),

            # 👉 chia cột (giữ chuẩn layout 8 cột)
            "c1": round_money(no),
            "c2": "",
            "c3": "",
            "c4": "",
            "c5": "",
            "c6": "",
        })

        total_no += no
        total_co += co

    # =============================
    # 🔥 TOTAL
    # =============================
    rows.append({
        "account": "CỘNG",
        "desc": "Cộng số phát sinh trong kỳ",
        "total": round_money(total_no - total_co),
        "c1": round_money(total_no),
        "c2": "",
        "c3": "",
        "c4": "",
        "c5": "",
        "c6": "",
    })

    return {
        "report_name": "SỔ CHI PHÍ SẢN XUẤT KINH DOANH (S36-DN)",
        "rows": rows,
        "generated_at": datetime.now(),
        "headers": [
            {"key": "account", "label": "Tài khoản"},
            {"key": "desc", "label": "Diễn giải"},
            {"key": "total", "label": "Tổng cộng"},
            {"key": "c1", "label": "C1"},
            {"key": "c2", "label": "C2"},
            {"key": "c3", "label": "C3"},
            {"key": "c4", "label": "C4"},
            {"key": "c5", "label": "C5"},
            {"key": "c6", "label": "C6"},
        ],
    }