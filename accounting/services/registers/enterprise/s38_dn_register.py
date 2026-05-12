# -*- coding: utf-8 -*-
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime


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
# 🔥 BUILD S38
# =============================

def build_s38_dn_register(data_list, account_filter=None):

    rows = []

    # =========================================
    # FIX account_filter
    # =========================================
    account_filter = (
        str(account_filter).strip()
        if account_filter else ""
    )

    total_debit = Decimal("0")
    total_credit = Decimal("0")

    # =========================================
    # GOM THEO CHỨNG TỪ
    # =========================================
    grouped = defaultdict(list)

    for row in (data_list or []):

        key = (
            str(row.get("number") or "").strip(),

            str(
                row.get("create_date")
                or row.get("signing_date")
                or ""
            ).strip()
        )

        grouped[key].append(row)

    # =========================================
    # XỬ LÝ TỪNG CHỨNG TỪ
    # =========================================
    for (doc_no, date), group_rows in grouped.items():

        first_row = group_rows[0] if group_rows else {}

        desc = (
            first_row.get("product_name")
            or first_row.get("desc")
            or ""
        )

        desc = str(desc).strip()

        debit_total = Decimal("0")
        credit_total = Decimal("0")

        contra_accounts = set()

        # =====================================
        # LOOP DÒNG CHỨNG TỪ
        # =====================================
        for row in group_rows:

            entries = row.get("entries") or []

            # =================================
            # FIX entries dạng JSON string
            # =================================
            if isinstance(entries, str):

                try:
                    entries = json.loads(entries)

                except Exception as e:
                    entries = []

            # =================================
            # FIX entries không phải list
            # =================================
            if not isinstance(entries, list):
                entries = []

            # =================================
            # LOOP ENTRY
            # =================================
            for entry in entries:

                if not isinstance(entry, dict):
                    continue

                debit = entry.get("debit")
                credit = entry.get("credit")

                amount = to_decimal(
                    entry.get("amount") or 0
                )

                debit_str = (
                    str(debit).strip()
                    if debit not in [None, ""]
                    else ""
                )

                credit_str = (
                    str(credit).strip()
                    if credit not in [None, ""]
                    else ""
                )

                # =============================
                # TK NỢ = account_filter
                # =============================
                if debit_str == account_filter:

                    debit_total += amount

                    if credit_str:
                        contra_accounts.add(credit_str)

                # =============================
                # TK CÓ = account_filter
                # =============================
                elif credit_str == account_filter:

                    credit_total += amount

                    if debit_str:
                        contra_accounts.add(debit_str)

        # =====================================
        # KHÔNG LIÊN QUAN TK
        # =====================================
        if debit_total == 0 and credit_total == 0:
            continue

        # =====================================
        # SORT TK ĐỐI ỨNG
        # =====================================
        contra_accounts_sorted = sorted(
            contra_accounts,
            key=lambda x: (
                0,
                int(str(x))
            ) if str(x).isdigit() else (
                1,
                str(x)
            )
        )

        # =====================================
        # APPEND ROW
        # =====================================
        rows.append({
            "date": date,
            "doc_no": doc_no,
            "desc": desc,
            "contra_account": ", ".join(
                contra_accounts_sorted
            ),
            "debit": round_money(debit_total),
            "credit": round_money(credit_total),
        })

        total_debit += debit_total
        total_credit += credit_total

    # =========================================
    # SORT THEO NGÀY
    # =========================================
    rows = sorted(
        rows,
        key=lambda x: (
            x.get("date") or "",
            x.get("doc_no") or ""
        )
    )

    # =========================================
    # DÒNG TỔNG
    # =========================================
    rows.append({
        "date": "",
        "doc_no": "",
        "desc": "CỘNG",
        "contra_account": "",
        "debit": round_money(total_debit),
        "credit": round_money(total_credit),
    })

    # =========================================
    # RETURN
    # =========================================
    return {
        "report_name": "SỔ CHI TIẾT CÁC TÀI KHOẢN (S38-DN)",
        "account": account_filter,
        "rows": rows,
        "generated_at": datetime.now(),
        "headers": [
            {
                "key": "date",
                "label": "Ngày CT"
            },
            {
                "key": "doc_no",
                "label": "Số CT"
            },
            {
                "key": "desc",
                "label": "Diễn giải"
            },
            {
                "key": "contra_account",
                "label": "TK Đối ứng"
            },
            {
                "key": "debit",
                "label": "PS Nợ"
            },
            {
                "key": "credit",
                "label": "PS Có"
            },
        ],
    }


#
# def build_s38_dn_register(data_list, account_filter=None):
#
#     rows = []
#
#     total_debit = Decimal("0")
#     total_credit = Decimal("0")
#
#     # =============================
#     # 🔥 1. GOM THEO CHỨNG TỪ
#     # =============================
#     grouped = defaultdict(list)
#
#     for row in data_list:
#         key = (
#             row.get("number"),
#             row.get("create_date") or row.get("signing_date")
#         )
#         grouped[key].append(row)
#
#     # =============================
#     # 🔥 2. XỬ LÝ TỪNG CHỨNG TỪ
#     # =============================
#     for (doc_no, date), group_rows in grouped.items():
#
#         desc = group_rows[0].get("product_name") or group_rows[0].get("desc") or ""
#
#         debit_total = Decimal("0")
#         credit_total = Decimal("0")
#         contra_accounts = set()
#
#         for row in group_rows:
#             for entry in row.get("entries", []):
#
#                 debit = entry.get("debit")
#                 credit = entry.get("credit")
#                 amount = to_decimal(entry.get("amount"))
#
#                 debit_str = str(debit) if debit else ""
#                 credit_str = str(credit) if credit else ""
#
#                 if not account_filter:
#                     continue
#
#                 # 🔥 TK ở bên Nợ
#                 if debit_str == account_filter:
#                     debit_total += amount
#                     if credit_str:
#                         contra_accounts.add(credit_str)
#
#                 # 🔥 TK ở bên Có
#                 elif credit_str == account_filter:
#                     credit_total += amount
#                     if debit_str:
#                         contra_accounts.add(debit_str)
#
#         # 🔥 Nếu không liên quan TK → bỏ
#         if debit_total == 0 and credit_total == 0:
#             continue
#
#         rows.append({
#             "date": date,
#             "doc_no": doc_no,
#             "desc": desc,
#             "contra_account": ", ".join(
#                 sorted(contra_accounts, key=lambda x: int(x) if x.isdigit() else x)
#             ),
#             "debit": round_money(debit_total),
#             "credit": round_money(credit_total),
#         })
#
#         total_debit += debit_total
#         total_credit += credit_total
#
#     # =============================
#     # 🔥 3. SORT THEO NGÀY
#     # =============================
#     rows = sorted(rows, key=lambda x: x["date"] or "")
#
#     # =============================
#     # 🔥 4. DÒNG TỔNG
#     # =============================
#     rows.append({
#         "date": "",
#         "doc_no": "",
#         "desc": "CỘNG",
#         "contra_account": "",
#         "debit": round_money(total_debit),
#         "credit": round_money(total_credit),
#     })
#
#     # =============================
#     # 🔥 5. RETURN
#     # =============================
#     return {
#         "report_name": "SỔ CHI TIẾT CÁC TÀI KHOẢN (S38-DN)",
#         "account": account_filter,
#         "rows": rows,
#         "generated_at": datetime.now(),
#         "headers": [
#             {"key": "date", "label": "Ngày CT"},
#             {"key": "doc_no", "label": "Số CT"},
#             {"key": "desc", "label": "Diễn giải"},
#             {"key": "contra_account", "label": "TK Đ ứng"},
#             {"key": "debit", "label": "PS Nợ"},
#             {"key": "credit", "label": "PS Có"},
#         ],
#     }