from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime
import json


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


def build_so_tien_gui(data_list):

    if not data_list:
        return {
            "report_name": "SỔ TIỀN GỬI NGÂN HÀNG (S08-DN)",
            "generated_at": datetime.now(),
            "rows": [],
            "account_number": ""
        }

    rows = []

    BANK_PREFIX = "112"

    opening_balance = Decimal("0")
    balance = opening_balance

    total_debit = Decimal("0")
    total_credit = Decimal("0")

    # =========================
    # 🔥 SỐ DƯ ĐẦU KỲ
    # =========================
    rows.append({
        "A": "",
        "B": "",
        "C": "",
        "D": "Số dư đầu kỳ",
        "E": "",
        "F": "",
        "debit": "",
        "credit": "",
        "balance": int(balance),
        "note": "Số dư đầu kỳ"
    })

    # =========================
    # 🔥 LOOP CHỨNG TỪ
    # =========================
    for row in data_list:

        # 🔥 FIX: nếu row là string
        if isinstance(row, str):
            try:
                row = json.loads(row)
            except:
                continue

        if not isinstance(row, dict):
            continue

        date = row.get("date") or ""
        voucher_no = row.get("number") or ""
        voucher_date = row.get("create_date") or ""
        desc = row.get("description") or row.get("product_name") or ""

        entries = (
            row.get("entries")
            or row.get("lines")
            or row.get("items")
            or []
        )

        # 🔥 FIX: entries là string
        if isinstance(entries, str):
            try:
                entries = json.loads(entries)
            except:
                entries = []

        if not isinstance(entries, list) or not entries:
            continue

        # =========================
        # 🔥 GOM DỮ LIỆU CHỨNG TỪ
        # =========================
        all_accounts = set()
        has_bank = False

        debit_entry = Decimal("0")
        credit_entry = Decimal("0")

        for e in entries:

            if not isinstance(e, dict):
                continue

            debit_acc = str(e.get("debit") or "")
            credit_acc = str(e.get("credit") or "")
            amount = round_money(to_decimal(e.get("amount")))

            # 🔥 gom tất cả tài khoản
            if debit_acc:
                all_accounts.add(debit_acc)
            if credit_acc:
                all_accounts.add(credit_acc)

            # 🔥 xác định phát sinh 112
            if debit_acc.startswith(BANK_PREFIX):
                debit_entry += amount
                has_bank = True

            elif credit_acc.startswith(BANK_PREFIX):
                credit_entry += amount
                has_bank = True

        # 🔥 không liên quan 112 → bỏ
        if not has_bank:
            continue

        # 🔥 TK đối ứng = tất cả TK trừ 112
        counter_accounts = sorted(
            acc for acc in all_accounts
            if not acc.startswith(BANK_PREFIX)
        )

        # 🔥 không có phát sinh tiền → bỏ
        if debit_entry == 0 and credit_entry == 0:
            continue

        # =========================
        # 🔥 CẬP NHẬT SỐ DƯ
        # =========================
        balance += debit_entry - credit_entry

        total_debit += debit_entry
        total_credit += credit_entry

        # =========================
        # 🔥 APPEND 1 DÒNG / CT
        # =========================
        rows.append({
            "A": date,
            "B": voucher_no,
            "C": voucher_date,
            "D": desc,
            "E": ", ".join(counter_accounts),
            "F": "",
            "debit": int(debit_entry) if debit_entry else "",
            "credit": int(credit_entry) if credit_entry else "",
            "balance": int(balance),
            "note": ""
        })

    # =========================
    # 🔥 CỘNG PHÁT SINH
    # =========================
    rows.append({
        "A": "",
        "B": "",
        "C": "",
        "D": "Cộng số phát sinh trong kỳ",
        "E": "",
        "F": "",
        "debit": int(total_debit),
        "credit": int(total_credit),
        "balance": "",
        "note": ""
    })

    # =========================
    # 🔥 SỐ DƯ CUỐI KỲ
    # =========================
    rows.append({
        "A": "",
        "B": "",
        "C": "",
        "D": "Số dư cuối kỳ",
        "E": "",
        "F": "",
        "debit": "",
        "credit": "",
        "balance": int(balance),
        "note": "Số dư cuối kỳ"
    })

    return {
        "report_name": "SỔ TIỀN GỬI NGÂN HÀNG (S08-DN)",
        "generated_at": datetime.now(),
        "rows": rows,
        "account_number": "112",  # 🔥 có thể replace bằng data thật
        "headers": [
            {"key": "B", "label": "Ngày ghi"},
            {"key": "C", "label": "Số CT"},
            {"key": "D", "label": "Ngày CT"},
            {"key": "E", "label": "Diễn giải"},
            {"key": "F", "label": "TK đối ứng"},
            {"key": "debit", "label": "Số thu"},
            {"key": "credit", "label": "Số chi"},
            {"key": "balance", "label": "Tồn"},
            {"key": "note", "label": "Ghi chú"},
        ],
    }

