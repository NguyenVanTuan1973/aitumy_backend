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


def build_s34_dn_register(data_list):

    rows = []

    # =============================
    # 🔥 GOM THEO ĐỐI TƯỢNG VAY
    # =============================
    borrower_map = {}

    for row in data_list:

        borrower = row.get("borrower") or row.get("partner") or "Không xác định"
        contract = row.get("contract_no") or ""

        entries = row.get("entries", [])

        if borrower not in borrower_map:
            borrower_map[borrower] = {
                "contract": contract,
                "ps_no": Decimal("0"),   # trả nợ gốc
                "ps_co": Decimal("0"),   # vay thêm
            }

        for entry in entries:

            amount = to_decimal(entry.get("amount"))

            debit = entry.get("debit")
            credit = entry.get("credit")

            # 🔥 chỉ TK 341
            if not (
                (debit and str(debit).startswith("341")) or
                (credit and str(credit).startswith("341"))
            ):
                continue

            # =============================
            # Có 341 → vay mới
            # =============================
            if credit and str(credit).startswith("341"):
                borrower_map[borrower]["ps_co"] += amount

            # =============================
            # Nợ 341 → trả nợ
            # =============================
            if debit and str(debit).startswith("341"):
                borrower_map[borrower]["ps_no"] += amount

    # =============================
    # 🔥 BUILD ROWS
    # =============================
    total_no = Decimal("0")
    total_co = Decimal("0")
    balance_total = Decimal("0")

    for borrower, val in borrower_map.items():

        ps_no = val["ps_no"]
        ps_co = val["ps_co"]

        balance = ps_co - ps_no   # vay - trả

        rows.append({
            "borrower": borrower,
            "contract": val["contract"],
            "due_date": "",
            "open": "",
            "ps_no": round_money(ps_no),
            "ps_co": round_money(ps_co),
            "balance": round_money(balance)
        })

        total_no += ps_no
        total_co += ps_co
        balance_total += balance

    # =============================
    # 🔥 TOTAL ROW
    # =============================
    rows.append({
        "borrower": "CỘNG",
        "contract": "",
        "due_date": "",
        "ps_no": round_money(total_no),
        "ps_co": round_money(total_co),
        "balance": round_money(balance_total)
    })

    return {
        "report_name": "SỔ CHI TIẾT TIỀN VAY (S34-DN)",
        "rows": rows,
        "generated_at": datetime.now(),
        "headers": [
            {"key": "borrower", "label": "Đối tượng vay"},
            {"key": "contract", "label": "Khế ước"},
            {"key": "due_date", "label": "Ngày đén hạn"},
            {"key": "ps_no", "label": "PS Nợ (trả)"},
            {"key": "ps_co", "label": "PS Có (vay)"},
            {"key": "balance", "label": "Số dư"},
        ],
    }