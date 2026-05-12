# -*- coding: utf-8 -*-

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime

# 🔥 Map tài khoản chi phí → khoản mục
COST_MAP = {
    "621": "c1",  # Nguyên vật liệu
    "622": "c2",  # Nhân công
    "623": "c3",  # Máy thi công
    "627": "c4",  # Sản xuất chung
    "641": "c5",  # Bán hàng
    "642": "c6",  # QLDN
}


# =============================
# 🔧 UTIL
# =============================
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


# =============================
# 🔥 BUILD S37
# =============================
def build_s37_dn_register(data_list, product_name="", month=None, year=None):

    # =============================
    # 🔥 1. GOM CHI PHÍ
    # =============================
    bucket = {
        "dd_dau_ky": {k: Decimal("0") for k in COST_MAP.values()},
        "phat_sinh": {k: Decimal("0") for k in COST_MAP.values()},
        "dd_cuoi_ky": {k: Decimal("0") for k in COST_MAP.values()},
    }

    for row in data_list:

        cost_stage = row.get("cost_type")  # dd_dau_ky | phat_sinh | dd_cuoi_ky
        entries = row.get("entries", [])

        if cost_stage not in bucket:
            continue

        for entry in entries:

            amount = to_decimal(entry.get("amount"))
            debit = str(entry.get("debit") or "")

            acc_prefix = debit[:3]

            if acc_prefix in COST_MAP:
                col = COST_MAP[acc_prefix]
                bucket[cost_stage][col] += amount

    # =============================
    # 🔥 2. BUILD 4 DÒNG CHUẨN
    # =============================
    rows = []

    def build_row(title, data_cols):
        total = sum(data_cols.values())

        return {
            "account": "",
            "desc": title,
            "total": round_money(total),

            "c1": round_money(data_cols["c1"]),
            "c2": round_money(data_cols["c2"]),
            "c3": round_money(data_cols["c3"]),
            "c4": round_money(data_cols["c4"]),
            "c5": round_money(data_cols["c5"]),
            "c6": round_money(data_cols["c6"]),
        }

    # 1. Dở dang đầu kỳ
    row1 = build_row("1. Chi phí SXKD dở dang đầu kỳ", bucket["dd_dau_ky"])

    # 2. Phát sinh
    row2 = build_row("2. Chi phí SXKD phát sinh trong kỳ", bucket["phat_sinh"])

    # 3. Giá thành = 1 + 2 - 4
    gia_thanh_cols = {}
    for k in COST_MAP.values():
        gia_thanh_cols[k] = (
            bucket["dd_dau_ky"][k]
            + bucket["phat_sinh"][k]
            - bucket["dd_cuoi_ky"][k]
        )

    row3 = build_row("3. Giá thành sản phẩm, dịch vụ", gia_thanh_cols)

    # 4. Dở dang cuối kỳ
    row4 = build_row("4. Chi phí SXKD dở dang cuối kỳ", bucket["dd_cuoi_ky"])

    rows.extend([row1, row2, row3, row4])

    # =============================
    # 🔥 3. TOTAL (optional)
    # =============================
    total_all = sum(r["total"] for r in rows)

    rows.append({
        "account": "CỘNG",
        "desc": "",
        "total": round_money(total_all),
        "c1": "",
        "c2": "",
        "c3": "",
        "c4": "",
        "c5": "",
        "c6": "",
    })

    # =============================
    # 🔥 4. RETURN
    # =============================
    return {
        "report_name": "THẺ TÍNH GIÁ THÀNH SẢN PHẨM, DỊCH VỤ (S37-DN)",
        "product_name": product_name,
        "period": f"Tháng {month}/{year}" if month and year else "",
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