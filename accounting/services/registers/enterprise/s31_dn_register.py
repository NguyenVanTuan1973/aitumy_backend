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


def build_s31_dn_register(data_list, account_type="131", partner_filter=None):
    """
    S31-DN - Sổ chi tiết thanh toán với người mua / người bán
    account_type: "131" (phải thu) | "331" (phải trả)
    """

    # =============================
    # 🔥 CHECK ĐỐI TƯỢNG
    # =============================
    if not partner_filter:
        return {
            "report_name": "S31-DN",
            "account": account_type,
            "partner": "",
            "rows": [],
            "generated_at": datetime.now(),  # 👈 thêm dòng này
            "headers": [],
            "error": "Vui lòng chọn Người mua / Người bán"
        }

    rows = []

    # =============================
    # 🔥 SỐ DƯ ĐẦU KỲ
    # =============================
    opening_no = Decimal("0")
    opening_co = Decimal("0")

    current_balance = Decimal("0")  # (+) Nợ, (-) Có

    rows.append({
        "ngay_ghi_so": "",
        "so_ct": "",
        "ngay_ct": "",
        "dien_giai": "Số dư đầu kỳ",
        "tk_doi_ung": "",
        "ps_no": "",
        "ps_co": "",
        "du_no": opening_no,
        "du_co": opening_co,
    })

    # =============================
    # 🔥 SẮP XẾP
    # =============================
    def parse_date(d):
        try:
            return datetime.strptime(str(d), "%d/%m/%Y")
        except:
            return datetime(1970, 1, 1)

    data_list = sorted(data_list, key=lambda x: parse_date(x.get("create_date")))

    total_ps_no = Decimal("0")
    total_ps_co = Decimal("0")

    # =============================
    # 🔥 LOOP CHỨNG TỪ
    # =============================
    for row in data_list:

        partner = (
            row.get("partner")
            or row.get("customer_name")
            or row.get("buyer_name")
            or row.get("seller_name")
        )

        if partner != partner_filter:
            continue

        entries = row.get("entries", [])
        if not entries:
            continue

        doc_no = row.get("number")
        date = row.get("create_date")
        desc = row.get("product_name") or "Hạch toán"

        # =============================
        # 🔥 TÍNH PHÁT SINH THEO TK 131/331
        # =============================
        ps_no = Decimal("0")
        ps_co = Decimal("0")
        tk_doi_ung = set()

        for entry in entries:
            amount = to_decimal(entry.get("amount"))

            debit = str(entry.get("debit") or "").strip()
            credit = str(entry.get("credit") or "").strip()

            if debit == account_type:
                ps_no += amount
                if credit:
                    tk_doi_ung.add(credit)

            elif credit == account_type:
                ps_co += amount
                if debit:
                    tk_doi_ung.add(debit)

        if ps_no == 0 and ps_co == 0:
            continue

        # =============================
        # 🔥 RUNNING BALANCE
        # =============================
        if account_type == "131":
            current_balance += ps_no - ps_co
        else:  # 331
            current_balance += ps_co - ps_no

        if current_balance >= 0:
            du_no = current_balance
            du_co = Decimal("0")
        else:
            du_no = Decimal("0")
            du_co = -current_balance

        # =============================
        # 🔥 ADD ROW
        # =============================
        rows.append({
            "ngay_ghi_so": date,
            "so_ct": doc_no,
            "ngay_ct": date,
            "dien_giai": desc,
            "tk_doi_ung": ",".join(tk_doi_ung),
            "ps_no": round_money(ps_no) if ps_no else "",
            "ps_co": round_money(ps_co) if ps_co else "",
            "du_no": round_money(du_no),
            "du_co": round_money(du_co),
        })

        total_ps_no += ps_no
        total_ps_co += ps_co

    # =============================
    # 🔥 CỘNG PHÁT SINH
    # =============================
    rows.append({
        "ngay_ghi_so": "",
        "so_ct": "",
        "ngay_ct": "",
        "dien_giai": "Cộng số phát sinh",
        "tk_doi_ung": "",
        "ps_no": round_money(total_ps_no),
        "ps_co": round_money(total_ps_co),
        "du_no": "",
        "du_co": "",
    })

    # =============================
    # 🔥 SỐ DƯ CUỐI KỲ
    # =============================
    if current_balance >= 0:
        end_no = current_balance
        end_co = Decimal("0")
    else:
        end_no = Decimal("0")
        end_co = -current_balance

    rows.append({
        "ngay_ghi_so": "",
        "so_ct": "",
        "ngay_ct": "",
        "dien_giai": "Số dư cuối kỳ",
        "tk_doi_ung": "",
        "ps_no": "",
        "ps_co": "",
        "du_no": round_money(end_no),
        "du_co": round_money(end_co),
    })

    # =============================
    return {
        "report_name": f"SỔ CHI TIẾT THANH TOÁN TK {account_type} (S31-DN)",
        "account": account_type,
        "partner": partner_filter,
        "rows": rows,
        "generated_at": datetime.now(),
        "headers": [
            {"key": "ngay_ghi_so", "label": "Ngày ghi sổ"},
            {"key": "so_ct", "label": "Số CT"},
            {"key": "ngay_ct", "label": "Ngày CT"},
            {"key": "dien_giai", "label": "Diễn giải"},
            {"key": "tk_doi_ung", "label": "TK đối ứng"},
            {"key": "ps_no", "label": "Phát sinh Nợ"},
            {"key": "ps_co", "label": "Phát sinh Có"},
            {"key": "du_no", "label": "Dư Nợ"},
            {"key": "du_co", "label": "Dư Có"},
        ],
    }


