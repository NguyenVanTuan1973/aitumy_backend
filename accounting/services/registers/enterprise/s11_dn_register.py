from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime


def to_decimal(val):
    try:
        if val is None or val == "":
            return Decimal("0")
        return Decimal(str(val))
    except:
        return Decimal("0")


def round_money(val):
    if not isinstance(val, Decimal):
        val = Decimal(str(val))
    return val.quantize(Decimal("1."), rounding=ROUND_HALF_UP)


def build_s11_dn_register(data_list):

    from decimal import Decimal
    from datetime import datetime

    product_map = {}

    # =====================================
    # TK ĐƯỢC PHÉP TRÊN S11-DN
    # =====================================
    VALID_ACCOUNTS = ("152", "153", "155", "156")

    # =====================================
    # GROUP THEO SẢN PHẨM
    # =====================================
    VALID_ACCOUNTS = ("152", "153", "155", "156")

    for row in data_list:

        product = row.get("product_name") or "Khác"
        entries = row.get("entries", [])

        nhap = Decimal("0")
        xuat = Decimal("0")

        # =========================
        # CHỈ TÍNH TK HỢP LỆ
        # =========================
        for entry in entries:

            amount = to_decimal(entry.get("amount"))

            debit = str(entry.get("debit") or "")
            credit = str(entry.get("credit") or "")

            # Nhập kho
            if debit.startswith(VALID_ACCOUNTS):
                nhap += amount

            # Xuất kho
            if credit.startswith(VALID_ACCOUNTS):
                xuat += amount

        # =========================
        # KHÔNG PHẢI TK KHO
        # => BỎ QUA
        # =========================
        if nhap == 0 and xuat == 0:
            continue

        # =========================
        # KHỞI TẠO PRODUCT
        # =========================
        if product not in product_map:
            product_map[product] = {
                "opening": Decimal("0"),
                "nhap": Decimal("0"),
                "xuat": Decimal("0")
            }

        product_map[product]["nhap"] += nhap
        product_map[product]["xuat"] += xuat

    # =====================================
    # BUILD ROWS
    # =====================================
    rows = []
    stt = 1

    total_open = Decimal("0")
    total_nhap = Decimal("0")
    total_xuat = Decimal("0")
    total_close = Decimal("0")

    for product, val in product_map.items():

        opening = val["opening"]
        nhap = val["nhap"]
        xuat = val["xuat"]

        closing = opening + nhap - xuat

        rows.append({
            "stt": stt,
            "ten": product,
            "ton_dau": round_money(opening),
            "nhap": round_money(nhap),
            "xuat": round_money(xuat),
            "ton_cuoi": round_money(closing)
        })

        stt += 1

        total_open += opening
        total_nhap += nhap
        total_xuat += xuat
        total_close += closing

    # =====================================
    # DÒNG TỔNG
    # =====================================
    rows.append({
        "stt": "",
        "ten": "Cộng",
        "ton_dau": round_money(total_open),
        "nhap": round_money(total_nhap),
        "xuat": round_money(total_xuat),
        "ton_cuoi": round_money(total_close)
    })

    return {
        "report_name": "BẢNG TỔNG HỢP VL, DC, SP, HH (S11-DN)",
        "rows": rows,
        "generated_at": datetime.now(),
        "headers": [
            {"key": "stt", "label": "STT"},
            {"key": "ten", "label": "Tên vật tư, hàng hóa"},
            {"key": "ton_dau", "label": "Tiền đầu kỳ"},
            {"key": "nhap", "label": "Tiền nhập"},
            {"key": "xuat", "label": "Tiền xuất"},
            {"key": "ton_cuoi", "label": "Tiền cuối kỳ"},
        ],
    }