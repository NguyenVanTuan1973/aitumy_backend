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


def build_s35_dn_register(data_list):

    rows = []

    total_qty = Decimal("0")
    total_revenue = Decimal("0")
    total_tax = Decimal("0")
    total_other = Decimal("0")

    for row in data_list:

        product = row.get("product_name") or "Hàng hóa"
        entries = row.get("entries", [])

        # 🔥 LẤY GIÁ TRỊ TỪ HEADER CHỨ KHÔNG LẤY ENTRY
        qty = to_decimal(row.get("quantity"))
        price = to_decimal(row.get("unit_price"))

        revenue = Decimal("0")
        tax = Decimal("0")
        other = Decimal("0")

        debit_accounts = set()
        credit_accounts = set()

        # =========================
        # 🔥 GỘP ENTRY
        # =========================
        for entry in entries:

            debit = entry.get("debit")
            credit = entry.get("credit")
            amount = to_decimal(entry.get("amount"))

            if credit:
                credit_accounts.add(str(credit))
            if debit:
                debit_accounts.add(str(debit))

            # DOANH THU
            if credit and str(credit).startswith("511"):
                revenue += amount

            # THUẾ
            if credit and (str(credit).startswith("333") or str(credit).startswith("521")):
                tax += amount

        # =========================
        # 🔥 1 CHỨNG TỪ = 1 DÒNG
        # =========================
        rows.append({
            "product": product,
            "date": row.get("create_date"),
            "doc_no": row.get("number"),
            "desc": row.get("description") or product,
            "qty": round_money(qty),
            "price": round_money(price),
            "amount": round_money(revenue),
            "tax": round_money(tax),
            "other": round_money(other),

            # 🔥 TK đối ứng (nếu cần)
            # "account": ", ".join(sorted((debit_accounts | credit_accounts)))
        })

        total_qty += qty
        total_revenue += revenue
        total_tax += tax
        total_other += other

    # =============================
    # 🔥 DÒNG CỘNG
    # =============================
    rows.append({
        "product": "CỘNG",
        "date": "",
        "doc_no": "",
        "desc": "",
        "qty": round_money(total_qty),
        "price": "",
        "amount": round_money(total_revenue),
        "tax": round_money(total_tax),
        "other": round_money(total_other),
        # "account": ""
    })

    net_revenue = total_revenue - total_tax - total_other

    rows.append({
        "product": "Doanh thu thuần",
        "date": "",
        "doc_no": "",
        "desc": "",
        "qty": "",
        "price": "",
        "amount": round_money(net_revenue),
        "tax": "",
        "other": "",  # Đảm bảo key 'other' luôn tồn tại
    })

    return {
        "report_name": "SỔ CHI TIẾT BÁN HÀNG (S35-DN)",
        "rows": rows,
        "generated_at": datetime.now(),
        "headers": [
            {"key": "date", "label": "Ngày CT"},
            {"key": "doc_no", "label": "Số CT"},
            {"key": "desc", "label": "Diễn giải"},
            {"key": "qty", "label": "Số lượng"},
            {"key": "price", "label": "Đơn giá"},
            {"key": "amount", "label": "Thành tiền"},
            {"key": "tax", "label": "Thuế"},
            {"key": "other", "label": "Khác"},
        ],
    }

