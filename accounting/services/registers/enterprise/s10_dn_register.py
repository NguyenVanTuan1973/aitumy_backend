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
    if val is None or val == "":
        return ""
    if not isinstance(val, Decimal):
        val = Decimal(str(val))  # 🔥 ép kiểu
    return val.quantize(Decimal("1."), rounding=ROUND_HALF_UP)


def build_s10_dn_register(data_list, product_filter=None):

    """
    SỔ CHI TIẾT VẬT LIỆU, HÀNG HÓA (S10-DN)

    - Chỉ lấy property = hàng hóa
    - Group theo product_name
    - Cho phép filter theo product
    - invoice_in  => nhập
    - invoice_out => xuất
    """

    from decimal import Decimal
    from datetime import datetime

    rows = []

    # =====================================
    # 🔥 DANH SÁCH HÀNG HÓA
    # =====================================
    product_options = []

    seen_products = set()

    for row in data_list:

        property_name = (
            row.get("tính chất")
            or row.get("property")
            or ""
        ).strip().lower()

        if property_name != "hàng hóa":
            continue

        product_name = str(
            row.get("tên hàng hóa, dịch vụ")
            or row.get("product_name")
            or "Khác"
        ).strip()

        if not product_name:
            continue

        if product_name not in seen_products:

            seen_products.add(product_name)

            product_options.append({
                "value": product_name,
                "label": product_name
            })

    # =====================================
    # 🔥 SỐ DƯ ĐẦU
    # =====================================
    current_qty = Decimal("0")
    current_amount = Decimal("0")

    rows.append({
        "so_ct": "",
        "ngay_ct": "",
        "dien_giai": "Số dư đầu kỳ",
        "tai_khoan": "",
        "don_gia": "",
        "nhap_sl": "",
        "nhap_tien": "",
        "xuat_sl": "",
        "xuat_tien": "",
        "ton_sl": current_qty,
        "ton_tien": current_amount,
        "ghi_chu": ""
    })

    # =====================================
    # 🔥 XỬ LÝ CHI TIẾT
    # =====================================
    for row in data_list:

        property_name = (
            row.get("tính chất")
            or row.get("property")
            or ""
        ).strip().lower()

        # Chỉ lấy hàng hóa
        if property_name != "hàng hóa":
            continue

        product_name = (
            row.get("tên hàng hóa, dịch vụ")
            or row.get("product_name")
            or "Khác"
        ).strip()

        # Filter theo hàng hóa user chọn
        if product_filter and product_name != product_filter:
            continue

        entries = row.get("entries", [])

        if not entries:
            continue

        doc_no = row.get("number")
        date = row.get("create_date")

        desc = product_name

        qty = to_decimal(row.get("quantity"))

        # total_amount = sum(
        #     to_decimal(e.get("amount"))
        #     for e in entries
        # )
        # =====================================
        # 🔥 GIÁ TRỊ HÀNG KHÔNG BAO GỒM VAT
        # =====================================
        inventory_accounts = ("152", "153", "155", "156")

        total_amount = Decimal("0")

        for e in entries:

            debit = str(e.get("debit") or "").strip()
            credit = str(e.get("credit") or "").strip()

            amount = to_decimal(e.get("amount"))

            # NHẬP KHO
            if debit.startswith(inventory_accounts):

                total_amount += amount

            # XUẤT KHO
            elif credit.startswith(inventory_accounts):

                total_amount += amount

        invoice_type = row.get("invoice_type")

        nhap_sl = Decimal("0")
        nhap_tien = Decimal("0")

        xuat_sl = Decimal("0")
        xuat_tien = Decimal("0")

        # =====================================
        # 🔥 NHẬP
        # =====================================
        if invoice_type == "invoice_in":

            nhap_sl = qty
            nhap_tien = total_amount

            current_qty += qty
            current_amount += total_amount

        # =====================================
        # 🔥 XUẤT
        # =====================================
        elif invoice_type == "invoice_out":

            xuat_sl = qty
            xuat_tien = total_amount

            current_qty -= qty
            current_amount -= total_amount

        else:
            continue

        # =====================================
        # 🔥 ĐƠN GIÁ
        # =====================================
        don_gia = Decimal("0")

        if qty != 0:
            don_gia = total_amount / qty

        # =====================================
        # 🔥 TK ĐỐI ỨNG
        # =====================================
        debit_accounts = [
            str(e.get("debit") or "").strip()
            for e in entries
        ]

        credit_accounts = [
            str(e.get("credit") or "").strip()
            for e in entries
        ]

        tai_khoan = ""
        if invoice_type == "invoice_in":

            tai_khoan = ",".join(
                dict.fromkeys(
                    acc for acc in credit_accounts if acc
                )
            )

        elif invoice_type == "invoice_out":

            tai_khoan = ",".join(
                dict.fromkeys(
                    acc for acc in debit_accounts if acc
                )
            )

        # =====================================
        # 🔥 ADD ROW
        # =====================================
        rows.append({
            "so_ct": doc_no,
            "ngay_ct": date,
            "dien_giai": desc,
            "tai_khoan": tai_khoan,
            "don_gia": round_money(don_gia),
            "nhap_sl": nhap_sl if nhap_sl else "",
            "nhap_tien": round_money(nhap_tien) if nhap_tien else "",
            "xuat_sl": xuat_sl if xuat_sl else "",
            "xuat_tien": round_money(xuat_tien) if xuat_tien else "",
            "ton_sl": current_qty,
            "ton_tien": round_money(current_amount),
            "ghi_chu": ""
        })

    # =====================================
    # 🔥 TỔNG PHÁT SINH
    # =====================================
    total_nhap = sum(
        [
            r["nhap_tien"]
            for r in rows
            if isinstance(r["nhap_tien"], Decimal)
        ],
        Decimal("0")
    )

    total_xuat = sum(
        [
            r["xuat_tien"]
            for r in rows
            if isinstance(r["xuat_tien"], Decimal)
        ],
        Decimal("0")
    )

    rows.append({
        "so_ct": "",
        "ngay_ct": "",
        "dien_giai": "Cộng phát sinh",
        "tai_khoan": "",
        "don_gia": "",
        "nhap_sl": "",
        "nhap_tien": round_money(total_nhap),
        "xuat_sl": "",
        "xuat_tien": round_money(total_xuat),
        "ton_sl": current_qty,
        "ton_tien": round_money(current_amount),
        "ghi_chu": ""
    })

    # =====================================
    return {
        "report_name": "SỔ CHI TIẾT VẬT LIỆU, HÀNG HÓA (S10-DN)",

        # 🔥 FORM LIST CHO USER CHỌN
        "product_options": product_options,

        # 🔥 PRODUCT ĐANG XEM
        "selected_product": product_filter,

        "rows": rows,

        "generated_at": datetime.now(),

        "headers": [
            {"key": "so_ct", "label": "Số CT"},
            {"key": "ngay_ct", "label": "Ngày CT"},
            {"key": "dien_giai", "label": "Tên vật tư, hàng hóa"},
            {"key": "tai_khoan", "label": "TK Đ/Ứ"},
            {"key": "don_gia", "label": "Đơn giá"},
            {"key": "nhap_sl", "label": "SL nhập"},
            {"key": "nhap_tien", "label": "Tiền nhập"},
            {"key": "xuat_sl", "label": "SL xuất"},
            {"key": "xuat_tien", "label": "Tiền xuất"},
            {"key": "ton_sl", "label": "SL tồn"},
            {"key": "ton_tien", "label": "Tiền tồn"},
            {"key": "ghi_chu", "label": "Ghi chú"},
        ],
    }


"""
def build_s10_dn_register(data_list):
    
    # SỔ CHI TIẾT VẬT LIỆU, HÀNG HÓA (S10-DN)
    # FIX:
    # - Lấy quantity từ row
    # - Không loop sai entry
    # - Tính đúng nhập/xuất
    

    rows = []

    # =============================
    # 🔥 SỐ DƯ ĐẦU KỲ
    # =============================
    current_qty = Decimal("0")
    current_amount = Decimal("0")

    rows.append({
        "so_ct": "",
        "ngay_ct": "",
        "dien_giai": "Số dư đầu kỳ",
        "tai_khoan": "",
        "don_gia": "",
        "nhap_sl": "",
        "nhap_tien": "",
        "xuat_sl": "",
        "xuat_tien": "",
        "ton_sl": current_qty,
        "ton_tien": current_amount,
        "ghi_chu": ""
    })

    # =============================
    # 🔥 XỬ LÝ DỮ LIỆU
    # =============================
    for row in data_list:
        entries = row.get("entries", [])
        if not entries:
            continue

        doc_no = row.get("number")
        date = row.get("create_date")

        desc = (
            row.get("product_name")
            or row.get("description")
            or "Hạch toán"
        )

        # ✅ Quantity lấy từ row (QUAN TRỌNG)
        qty = to_decimal(row.get("quantity"))

        # ✅ Tổng tiền của chứng từ
        total_amount = sum(
            to_decimal(e.get("amount")) for e in entries
        )

        # ✅ Lấy danh sách tài khoản
        debit_accounts = [
            str(e.get("debit") or "").strip()
            for e in entries
        ]

        credit_accounts = [
            str(e.get("credit") or "").strip()
            for e in entries
        ]

        # =============================
        # 🔥 XÁC ĐỊNH NHẬP / XUẤT
        # =============================
        nhap_sl = Decimal("0")
        nhap_tien = Decimal("0")
        xuat_sl = Decimal("0")
        xuat_tien = Decimal("0")

        # Nhập kho (Nợ 152/156)
        if any(acc.startswith(("152", "156")) for acc in debit_accounts):
            nhap_sl = qty
            nhap_tien = total_amount

            current_qty += qty
            current_amount += total_amount

        # Xuất kho (Có 152/156)
        elif any(acc.startswith(("152", "156")) for acc in credit_accounts):
            xuat_sl = qty
            xuat_tien = total_amount

            current_qty -= qty
            current_amount -= total_amount

        else:
            continue

        # =============================
        # 🔥 ĐƠN GIÁ
        # =============================
        don_gia = Decimal("0")
        if qty != 0:
            don_gia = total_amount / qty

        # =============================
        # 🔥 CHỌN TK HIỂN THỊ
        # =============================
        tai_khoan = ""

        if nhap_sl > 0:
            tai_khoan = ",".join(
                acc for acc in debit_accounts if acc
            )
        elif xuat_sl > 0:
            tai_khoan = ",".join(
                acc for acc in credit_accounts if acc
            )

        # =============================
        # 🔥 ADD ROW
        # =============================
        rows.append({
            "so_ct": doc_no,
            "ngay_ct": date,
            "dien_giai": desc,
            "tai_khoan": tai_khoan,
            "don_gia": round_money(don_gia),
            "nhap_sl": nhap_sl if nhap_sl else "",
            "nhap_tien": round_money(nhap_tien) if nhap_tien else "",
            "xuat_sl": xuat_sl if xuat_sl else "",
            "xuat_tien": round_money(xuat_tien) if xuat_tien else "",
            "ton_sl": current_qty,
            "ton_tien": round_money(current_amount),
            "ghi_chu": ""
        })

    # =============================
    # 🔥 TỔNG CUỐI KỲ
    # =============================
    total_nhap = sum(
        [r["nhap_tien"] for r in rows if isinstance(r["nhap_tien"], Decimal)],
        Decimal("0")
    )

    total_xuat = sum(
        [r["xuat_tien"] for r in rows if isinstance(r["xuat_tien"], Decimal)],
        Decimal("0")
    )

    rows.append({
        "so_ct": "",
        "ngay_ct": "",
        "dien_giai": "Cộng phát sinh",
        "tai_khoan": "",
        "don_gia": "",
        "nhap_sl": "",
        "nhap_tien": round_money(total_nhap),
        "xuat_sl": "",
        "xuat_tien": round_money(total_xuat),
        "ton_sl": current_qty,
        "ton_tien": round_money(current_amount),
        "ghi_chu": ""
    })

    # =============================
    return {
        "report_name": "SỔ CHI TIẾT VẬT LIỆU, HÀNG HÓA (S10-DN)",
        "rows": rows,
        "generated_at": datetime.now(),
        "headers": [
            {"key": "so_ct", "label": "Số CT"},
            {"key": "ngay_ct", "label": "Ngày CT"},
            {"key": "dien_giai", "label": "Tên vật tư, hàng hóa"},
            {"key": "tai_khoan", "label": "TK Đ/Ứ"},
            {"key": "don_gia", "label": "Đơn giá"},
            {"key": "nhap_sl", "label": "SL nhập"},
            {"key": "nhap_tien", "label": "Tiền nhập"},
            {"key": "xuat_sl", "label": "SL xuất"},
            {"key": "xuat_tien", "label": "Tiền xuất"},
            {"key": "ton_sl", "label": "SL tồn"},
            {"key": "ton_tien", "label": "Tiền tồn"},
            {"key": "ghi_chu", "label": "Ghi chú"},
        ],
    }
    
"""