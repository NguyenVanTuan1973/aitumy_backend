from decimal import Decimal
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

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

def build_s41a_dn_register(data_list):
    companies = {}
    for row in data_list:
        company = row.get("company_name") or "Không xác định"
        if company not in companies:
            companies[company] = {
                "rows": [],
                "opening": Decimal("0"),
                "closing": Decimal("0"),
                "sum_adj_2": Decimal("0"),
                "sum_adj_3": Decimal("0"),
                "sum_adj_4": Decimal("0"),
                "sum_adj_5": Decimal("0"),
            }

        # Dùng hàm to_decimal bạn đã viết để an toàn
        opening = to_decimal(row.get("opening_value"))
        adj_2 = to_decimal(row.get("adjustment"))
        adj_3 = to_decimal(row.get("profit_loss"))
        adj_4 = to_decimal(row.get("adj_diff_date"))
        adj_5 = to_decimal(row.get("adj_policy"))
        adj_6 = to_decimal(row.get("equity_change"))

        closing = opening + adj_2 + adj_3 + adj_4 + adj_5 + adj_6

        companies[company]["rows"].append({
            "date": row.get("date") or "",
            "doc_no": row.get("doc_no") or "",
            "desc": row.get("desc") or "",
            "opening": Decimal(opening), # Convert sang float để JSON nhận diện
            "adj_2": Decimal(adj_2),
            "adj_3": Decimal(adj_3),
            "adj_4": Decimal(adj_4),
            "adj_5": Decimal(adj_5),
            "adj_6": Decimal(adj_6),
            "closing": Decimal(closing),
        })

        companies[company]["opening"] += opening
        companies[company]["closing"] += closing
        companies[company]["sum_adj_2"] += adj_2
        # ... cộng các tổng khác ...

    # Trước khi return, hãy convert các trường tổng hợp sang float
    for name in companies:
        c = companies[name]
        c["opening"] = Decimal(c["opening"])
        c["closing"] = Decimal(c["closing"])
        c["sum_adj_2"] = Decimal(c["sum_adj_2"])
        c["sum_adj_3"] = Decimal(c["sum_adj_3"])
        c["sum_adj_4"] = Decimal(c["sum_adj_4"])
        c["sum_adj_5"] = Decimal(c["sum_adj_5"])

    return companies