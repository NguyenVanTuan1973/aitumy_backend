from decimal import Decimal
from datetime import datetime
from collections import defaultdict


def _to_decimal(value):
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def build_nhat_ky_chung(data):
    """
    S03a-DN - Sổ Nhật ký chung
    Chuẩn hóa từ dữ liệu hóa đơn có nhiều entries
    """

    # --- 1. Parse ngày ---
    def parse_date(d):
        if isinstance(d, datetime):
            return d
        try:
            return datetime.strptime(str(d), "%d/%m/%Y")
        except:
            return datetime(1970, 1, 1)

    # --- 2. Flatten dữ liệu ---
    flat_entries = []

    for doc in data:
        doc_no = doc.get("number")
        date_ct = doc.get("create_date")
        description = doc.get("product_name") or doc.get("desc") or ""

        for line in doc.get("entries", []):
            flat_entries.append({
                "doc_no": doc_no,
                "date_ct": date_ct,
                "description": description,
                "debit_account": line.get("debit"),
                "credit_account": line.get("credit"),
                "amount": _to_decimal(line.get("amount")),
            })

    # --- 3. Sắp xếp ---
    flat_entries = sorted(flat_entries, key=lambda x: (
        parse_date(x.get("date_ct")),
        str(x.get("doc_no", ""))
    ))

    # --- 4. Gom nhóm theo chứng từ ---
    grouped = defaultdict(list)
    for e in flat_entries:
        key = (
            e.get("doc_no"),
            e.get("date_ct"),
            e.get("description")
        )
        grouped[key].append(e)

    rows = []
    stt = 1
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    # --- 5. Build rows ---
    for (doc_no, date_ct, description), group_rows in grouped.items():
        first_line = True

        for r in group_rows:
            amount = _to_decimal(r.get("amount"))

            debit_acc = r.get("debit_account")
            credit_acc = r.get("credit_account")

            # --- Dòng NỢ ---
            if debit_acc:
                rows.append({
                    "stt": stt if first_line else "",
                    "so_ct": doc_no if first_line else "",
                    "ngay_ct": date_ct if first_line else "",
                    "dien_giai": description if first_line else "",
                    "tai_khoan": debit_acc,
                    "ps_no": amount,
                    "ps_co": None
                })
                total_debit += amount
                first_line = False

            # --- Dòng CÓ ---
            if credit_acc:
                rows.append({
                    "stt": "",
                    "so_ct": "",
                    "ngay_ct": "",
                    "dien_giai": "",
                    "tai_khoan": credit_acc,
                    "ps_no": None,
                    "ps_co": amount
                })
                total_credit += amount

        stt += 1

    # --- 6. Dòng tổng ---
    rows.append({
        "stt": "",
        "so_ct": "",
        "ngay_ct": "",
        "dien_giai": "Cộng số phát sinh",
        "tai_khoan": "",
        "ps_no": total_debit,
        "ps_co": total_credit
    })

    # --- 7. Return chuẩn cho export ---
    return {
        "report_name": "SỔ NHẬT KÝ CHUNG (S03a-DN)",
        "generated_at": datetime.now().isoformat(),
        "rows": rows,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "headers": [
            {"key": "stt", "label": "STT"},
            {"key": "so_ct", "label": "Số CT"},
            {"key": "ngay_ct", "label": "Ngày CT"},
            {"key": "dien_giai", "label": "Diễn giải"},
            {"key": "tai_khoan", "label": "TK Đ/Ứ"},
            {"key": "ps_no", "label": "PS Nợ"},
            {"key": "ps_co", "label": "PS Có"},
        ],
    }