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


def build_s07a_dn_register(data_list):

    rows = []

    # 🔥 SỐ DƯ ĐẦU KỲ (tạm = 0)
    opening = Decimal("0")
    balance = opening

    rows.append({
        "type": "opening",
        "dien_giai": "Số tồn đầu kỳ",
        "ton": round_money(balance)
    })

    total_no = Decimal("0")
    total_co = Decimal("0")

    # =============================
    # 🔥 PHÁT SINH
    # =============================
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

        all_accounts = set()
        has_cash = False

        debit_entry = Decimal("0")
        credit_entry = Decimal("0")

        # =========================
        # 🔥 GOM THEO CHỨNG TỪ
        # =========================
        for entry in entries:

            if not isinstance(entry, dict):
                continue

            amount = to_decimal(entry.get("amount"))

            debit = str(entry.get("debit") or "")
            credit = str(entry.get("credit") or "")

            # 🔥 gom toàn bộ tài khoản
            if debit:
                all_accounts.add(debit)
            if credit:
                all_accounts.add(credit)

            # 🔥 xác định TK 111
            if debit.startswith("111"):
                debit_entry += amount
                has_cash = True

            elif credit.startswith("111"):
                credit_entry += amount
                has_cash = True

        # ❌ không liên quan 111 → bỏ
        if not has_cash:
            continue

        # 🔥 TK đối ứng = tất cả TK trừ 111
        counter_accounts = [
            acc for acc in all_accounts
            if not acc.startswith("111")
        ]

        # =========================
        # 🔥 UPDATE SỐ DƯ
        # =========================
        balance += debit_entry - credit_entry

        total_no += debit_entry
        total_co += credit_entry

        rows.append({
            "type": "data",
            "ngay_ghi": date,
            "ngay_ct": date,
            "so_ct": doc_no,
            "dien_giai": desc,
            "tk_doi_ung": ", ".join(sorted(counter_accounts)),
            "no": round_money(debit_entry) if debit_entry else "",
            "co": round_money(credit_entry) if credit_entry else "",
            "ton": round_money(balance),
            "ghi_chu": ""
        })

    # =============================
    # 🔥 CỘNG PHÁT SINH
    # =============================
    rows.append({
        "type": "total_ps",
        "dien_giai": "Cộng số phát sinh trong kỳ",
        "no": round_money(total_no),
        "co": round_money(total_co)
    })

    # =============================
    # 🔥 TỒN CUỐI
    # =============================
    rows.append({
        "type": "closing",
        "dien_giai": "Số tồn cuối kỳ",
        "ton": round_money(balance)
    })

    return {
        "report_name": "SỔ KẾ TOÁN CHI TIẾT QUỸ TIỀN MẶT (S07a-DN)",
        "rows": rows,
        "generated_at": datetime.now(),
        "headers": [
            {"key": "ngay_ghi", "label": "Ngày ghi"},
            {"key": "ngay_ct", "label": "Ngày CT"},
            {"key": "so_ct", "label": "Số CT"},
            {"key": "dien_giai", "label": "Diễn giải"},
            {"key": "tk_doi_ung", "label": "TK Đ Ư"},
            {"key": "no", "label": "PS Nợ"},
            {"key": "co", "label": "PS Có"},
            {"key": "ton", "label": "Tồn"},
            {"key": "ghi_chu", "label": "Ghi chú"},
        ],
    }