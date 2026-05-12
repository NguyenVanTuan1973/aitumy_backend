import json
import re
import traceback

import unicodedata

from django.contrib import messages
import pandas as pd
from django.shortcuts import render
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
import math

from accounting.services.registers.enterprise.voucher_journal.s05_dn_register import build_so_cai
from accounting.services.registers.enterprise.shared_diary.s03a_dn_register import build_nhat_ky_chung
from accounting.services.registers.enterprise.s08_dn_register import build_so_tien_gui
from accounting.services.registers.enterprise.s61_dn_register import build_s61_dn_register
from accounting.services.registers.enterprise.s10_dn_register import build_s10_dn_register
from accounting.services.registers.enterprise.s11_dn_register import build_s11_dn_register
from accounting.services.registers.enterprise.s12_dn_register import build_s12_dn_register
from accounting.services.registers.enterprise.s06_dn_register import build_s06_dn_register
from accounting.services.registers.enterprise.s07_dn_register import build_s07_dn_register
from accounting.services.registers.enterprise.s07a_dn_register import build_s07a_dn_register
from accounting.services.registers.enterprise.s31_dn_register import build_s31_dn_register
from accounting.services.registers.enterprise.s34_dn_register import build_s34_dn_register
from accounting.services.registers.enterprise.s35_dn_register import build_s35_dn_register
from accounting.services.registers.enterprise.s36_dn_register import build_s36_dn_register
from accounting.services.registers.enterprise.ledger_journal.s01_dn_register import build_so1_dn_register
from accounting.services.registers.enterprise.s37_dn_register import build_s37_dn_register
from accounting.services.registers.enterprise.s38_dn_register import build_s38_dn_register
from accounting.services.registers.enterprise.s41a_dn_register import build_s41a_dn_register


def login_view(request):
    return render(request, "accounting/website/login.html")

def logout_view(request):
    logout(request)
    return redirect("accounting_login")

def dashboard(request):
    return render(request, "accounting/website/base.html")


def upload_view(request):
    return render(request, "accounting/website/upload.html")


# 🔥 helper chống NaN
def safe_float(val):
    """
    Convert mọi kiểu dữ liệu về float an toàn:
    - None, NaN → 0
    - "1,000" → 1000
    - "1.000.000" → 1000000
    - " 2000 " → 2000
    """

    if val is None:
        return 0

    # pandas NaN
    if isinstance(val, float) and math.isnan(val):
        return 0

    # xử lý string
    if isinstance(val, str):
        val = val.strip()

        if val == "":
            return 0

        # bỏ dấu phân cách
        val = val.replace(",", "").replace(".", "")

        # giữ lại số và dấu -
        val = re.sub(r"[^\d\-]", "", val)

        if val == "" or val == "-":
            return 0

    try:
        return float(val)
    except:
        return 0


def normalize_text(text):
    """Bỏ dấu tiếng Việt + upper"""
    if not text:
        return ""
    text = str(text).strip()

    # bỏ dấu
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')

    return text.upper()


def detect_payment_method(value):
    """
    Chuẩn hóa về: cash | bank | debt
    """

    if value is None or pd.isna(value) or value == 0:
        return "debt"

    val = normalize_text(value)

    # 🔥 ưu tiên BANK trước (quan trọng)
    BANK_KEYWORDS = [
        "CK", "CHUYEN KHOAN", "NGAN HANG",
        "BANK", "TRANSFER", "UNC"
    ]

    CASH_KEYWORDS = [
        "TM", "TIEN MAT", "CASH"
    ]

    # =============================
    # 🔥 MATCH
    # =============================
    if any(k in val for k in BANK_KEYWORDS):
        return "bank"

    if any(k in val for k in CASH_KEYWORDS):
        return "cash"

    return "debt"

# 🔥 hardcode MST doanh nghiệp (sau này lấy từ user)
USER_TAX_CODE = "0317982468"

"""Chuẩn hóa MST: bỏ ký tự lạ"""
def normalize_tax_code(tax_code):
    if not tax_code:
        return ""

    val = str(tax_code).strip()

    # 🔥 bỏ .0 từ Excel
    if val.endswith(".0"):
        val = val[:-2]

    # 🔥 chỉ giữ số
    val = re.sub(r"\D", "", val)

    # 🔥 bỏ số 0 đầu (để match)
    val = val.lstrip("0")

    return val

def format_tax_code(tax_code):
    if not tax_code:
        return ""

    val = re.sub(r"\D", "", str(tax_code))

    # 🔥 đảm bảo đủ 10 số (padding lại)
    if len(val) == 9:
        val = "0" + val

    return val

"""API dùng chung cho in / out"""
@csrf_exempt
def api_upload_invoice(request):

    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    excel_file = request.FILES.get("excel_file")

    if not excel_file:
        return JsonResponse({"error": "No file uploaded"}, status=400)

    try:

        df = pd.read_excel(excel_file)

        # 🔥 loại NaN
        df = df.fillna(0)

        # chuẩn hóa column
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace("\n", " ")
            .str.replace("  ", " ")
        )

        data = []

        user_tax = normalize_tax_code(USER_TAX_CODE)

        for i, row in df.iterrows():
            try:
                raw_payment_val = row.get("hình thức thanh toán", "")

                seller_tax = normalize_tax_code(
                    row.get("mst người bán/mst người xuất hàng", "")
                )

                buyer_tax = normalize_tax_code(
                    row.get("mst người mua/mst người nhận hàng", "")
                )

                # =============================
                # 🔥 XÁC ĐỊNH LOẠI HÓA ĐƠN
                # =============================
                invoice_type = "unknown"

                if buyer_tax == user_tax:
                    invoice_type = "invoice_in"      # mua vào

                elif seller_tax == user_tax:
                    invoice_type = "invoice_out"     # bán ra


                # =============================
                item = {
                    "id": i + 1,

                    "invoice_type": invoice_type,  # 🔥 QUAN TRỌNG
                    "number": str(row.get("số hóa đơn", "")),
                    "create_date": str(row.get("ngày lập", "")),

                    "template": row.get("ký hiệu mẫu số", ""),
                    "symbol": row.get("ký hiệu hóa đơn", ""),

                    "signing_date": str(row.get("ngày người bán ký số", "")),
                    "mccqt": str(row.get("mccqt", "")),
                    "cqt_signing_date": str(row.get("ngày cqt ký số", "")),

                    "currency": row.get("đơn vị tiền tệ", "VND"),
                    "exchange": safe_float(row.get("tỷ giá")),

                    "seller_name": row.get("tên người bán/tên người xuất hàng", ""),
                    "seller_tax_code": seller_tax,
                    "seller_address": row.get("địa chỉ người bán", ""),

                    "buyer_name": row.get("tên người mua/tên người nhận hàng", ""),
                    "buyer_tax_code": buyer_tax,
                    "buyer_address": row.get("địa chỉ người mua", ""),

                    "delivery_address": row.get("địa chỉ giao hàng", ""),
                    "license_plate": row.get("số phương tiện", ""),
                    "customer_code": row.get("mã khách hàng", ""),
                    "id_card": row.get("căn cước công dân", ""),

                    "payment": detect_payment_method(raw_payment_val),

                    "property": row.get("tính chất", ""),
                    "material_code": row.get("mã vật tư", ""),
                    "material_series": row.get("số lô", ""),
                    "expiration_date": str(row.get("hạn sử dụng", "")),

                    "product_name": row.get("tên hàng hóa, dịch vụ", ""),
                    "product_unit": row.get("đơn vị tính", ""),

                    "quantity": safe_float(row.get("số lượng")),
                    "unit_price": safe_float(row.get("đơn giá")),
                    "discount": safe_float(row.get("chiết khấu")),
                    "tax_rate": safe_float(row.get("thuế suất")),
                    "amount": safe_float(row.get("thành tiền chưa thuế")),
                    "tax": safe_float(row.get("tiền thuế")),
                    "discount_total": safe_float(row.get("tổng tiền chiết khấu thương mại")),
                    "fee_total": safe_float(row.get("tổng tiền phí")),
                    "payment_total": safe_float(row.get("tổng tiền thanh toán")),

                    "invoice_status": row.get("trạng thái hóa đơn", ""),
                    "associated_invoice_status": row.get("hóa đơn liên quan", ""),
                    "invoice_check_result": row.get("kết quả kiểm tra hóa đơn", ""),

                    "lookup_link": row.get("link tra cứu", ""),
                    "lookup_code": row.get("mã tra cứu", ""),

                    "posted": False,
                    "pdf": None,
                }

                data.append(item)

            except Exception as e:
                data.append({
                    "id": i + 1,
                    "error": str(e)
                })

        return JsonResponse({
            "status": "success",
            "count": len(data),
            "data": data
        })

    except Exception as e:
        return JsonResponse({
            "error": str(e)
        }, status=500)

def api_update_row(request):
    if request.method == "POST":
        row_id = request.POST.get("id")
        payment = request.POST.get("payment")
        posted = request.POST.get("posted")

        # TODO: update DB

        return JsonResponse({"status": "ok"})

# ===== Sau này sẽ bỏ 2 api này ====
@csrf_exempt
def api_upload_invoice_in(request):

    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    excel_file = request.FILES.get("excel_file")

    if not excel_file:
        return JsonResponse({"error": "No file uploaded"}, status=400)

    try:
        # 🔥 đọc Excel
        df = pd.read_excel(excel_file)

        # 🔥 FIX CỨNG: loại toàn bộ NaN
        df = df.fillna(0)

        # chuẩn hóa column
        df.columns = df.columns.str.strip().str.lower()

        data = []

        for i, row in df.iterrows():
            try:
                raw_payment_val = row.get("hình thức thanh toán", "")

                item = {
                    "id": i + 1,

                    "template": row.get("ký hiệu mẫu số", ""),
                    "symbol": row.get("ký hiệu hóa đơn", ""),
                    "number": str(row.get("số hóa đơn", "")),
                    "create_date": str(row.get("ngày lập", "")),
                    "signing_date": str(row.get("ngày người bán ký số", "")),
                    "mccqt": str(row.get("mccqt", "")),
                    "cqt_signing_date": str(row.get("ngày cqt ký số", "")),
                    "currency": row.get("đơn vị tiền tệ", "VND"),
                    "exchange": safe_float(row.get("tỷ giá")),
                    "seller_name": row.get("tên người bán/tên người xuất hàng", ""),
                    "seller_tax_code": str(row.get("mst người bán/mst người xuất hàng", "")),
                    "seller_address": row.get("địa chỉ người bán", ""),
                    "buyer_name": row.get("tên người mua/tên người nhận hàng", ""),
                    "buyer_tax_code": str(row.get("mst người mua/MST người nhận hàng", "")),
                    "buyer_address": row.get("địa chỉ người mua", ""),
                    "delivery_address": row.get("địa chỉ giao hàng", ""),
                    "license_plate": row.get("số phương tiện", ""),
                    "customer_code": row.get("mã khách hàng", ""),
                    "id_card": row.get("căn cước công dân", ""),

                    "payment": detect_payment_method(raw_payment_val),

                    "property": row.get("tính chất", ""),
                    "material_code": row.get("mã vật tư", ""),
                    "material_series": row.get("số lô", ""),
                    "expiration_date": str(row.get("hạn sử dụng", "")),
                    "product_name": row.get("tên hàng hóa, dịch vụ", ""),
                    "product_unit": row.get("đơn vị tính", ""),

                    # 🔥 dùng safe_float
                    "quantity": safe_float(row.get("số lượng")),
                    "unit_price": safe_float(row.get("Đơn giá")),
                    "discount": safe_float(row.get("chiết khấu")),
                    "tax_rate": safe_float(row.get("thuế suất")),
                    "amount": safe_float(row.get("thành tiền chưa thuế")),
                    "tax": safe_float(row.get("tiền thuế")),
                    "discount_total": safe_float(row.get("tổng tiền chiết khấu thương mại")),
                    "fee_total": safe_float(row.get("tổng tiền phí")),
                    "payment_total": safe_float(row.get("tổng tiền thanh toán")),

                    "invoice_status": row.get("trạng thái hóa đơn", ""),
                    "Associated_invoice_status": row.get("hóa đơn liên quan", ""),
                    "invoice_check_result": row.get("kết quả kiểm tra hóa đơn", ""),
                    "lookup_link": row.get("link tra cứu", ""),
                    "lookup_code": row.get("mã tra cứu", ""),

                    "posted": False,
                    "pdf": None,
                }

                data.append(item)

            except Exception as e:
                data.append({
                    "id": i + 1,
                    "error": str(e)
                })

        return JsonResponse({
            "status": "success",
            "count": len(data),
            "data": data
        })


    except Exception as e:
        return JsonResponse({
            "error": str(e)
        }, status=500)

@csrf_exempt
def api_upload_invoice_out(request):

    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    excel_file = request.FILES.get("excel_file")

    if not excel_file:
        return JsonResponse({"error": "No file uploaded"}, status=400)

    try:
        # 🔥 đọc Excel
        df = pd.read_excel(excel_file)

        # 🔥 FIX CỨNG: loại toàn bộ NaN
        df = df.fillna(0)

        # chuẩn hóa column
        df.columns = df.columns.str.strip().str.lower()

        data = []

        for i, row in df.iterrows():
            try:

                raw_payment_val = row.get("hình thức thanh toán", "")

                item = {
                    "id": i + 1,

                    "template": row.get("ký hiệu mẫu số", ""),
                    "symbol": row.get("ký hiệu hóa đơn", ""),
                    "number": str(row.get("số hóa đơn", "")),
                    "create_date": str(row.get("ngày lập", "")),
                    "signing_date": str(row.get("ngày người bán ký số", "")),
                    "mccqt": str(row.get("mccqt", "")),
                    "cqt_signing_date": str(row.get("ngày cqt ký số", "")),
                    "currency": row.get("đơn vị tiền tệ", "VND"),
                    "exchange": safe_float(row.get("tỷ giá")),
                    "seller_name": row.get("tên người bán/tên người xuất hàng", ""),
                    "seller_tax_code": str(row.get("mst người bán/mst người xuất hàng", "")),
                    "seller_address": row.get("địa chỉ người bán", ""),
                    "buyer_name": row.get("tên người mua/tên người nhận hàng", ""),
                    "buyer_tax_code": str(row.get("mst người mua/MST người nhận hàng", "")),
                    "buyer_address": row.get("địa chỉ người mua", ""),
                    "delivery_address": row.get("địa chỉ giao hàng", ""),
                    "license_plate": row.get("số phương tiện", ""),
                    "customer_code": row.get("mã khách hàng", ""),
                    "id_card": row.get("căn cước công dân", ""),

                    "payment": detect_payment_method(raw_payment_val),

                    "property": row.get("tính chất", ""),
                    "material_code": row.get("mã vật tư", ""),
                    "material_series": row.get("số lô", ""),
                    "expiration_date": str(row.get("hạn sử dụng", "")),
                    "product_name": row.get("tên hàng hóa, dịch vụ", ""),
                    "product_unit": row.get("đơn vị tính", ""),

                    # 🔥 dùng safe_float
                    "quantity": safe_float(row.get("số lượng")),
                    "unit_price": safe_float(row.get("Đơn giá")),
                    "discount": safe_float(row.get("chiết khấu")),
                    "tax_rate": safe_float(row.get("thuế suất")),
                    "amount": safe_float(row.get("thành tiền chưa thuế")),
                    "tax": safe_float(row.get("tiền thuế")),
                    "discount_total": safe_float(row.get("tổng tiền chiết khấu thương mại")),
                    "fee_total": safe_float(row.get("tổng tiền phí")),
                    "payment_total": safe_float(row.get("tổng tiền thanh toán")),

                    "invoice_status": row.get("trạng thái hóa đơn", ""),
                    "Associated_invoice_status": row.get("hóa đơn liên quan", ""),
                    "invoice_check_result": row.get("kết quả kiểm tra hóa đơn", ""),
                    "lookup_link": row.get("link tra cứu", ""),
                    "lookup_code": row.get("mã tra cứu", ""),

                    "posted": False,
                    "pdf": None,
                }

                data.append(item)

            except Exception as e:
                data.append({
                    "id": i + 1,
                    "error": str(e)
                })

        return JsonResponse({
            "status": "success",
            "count": len(data),
            "data": data
        })

    except Exception as e:
        return JsonResponse({
            "error": str(e)
        }, status=500)

# ==========================


# Đang ký số dư đầu
def opening_balance_view(request):
    """
    View để quản lý việc nhập Số dư đầu kỳ cho nhiều đối tượng.
    """
    if request.method == 'POST':

        try:

            messages.success(request, "Đã lưu số dư đầu kỳ thành công!")
            return redirect('accounting/opening_balance/')

        except Exception as e:
            messages.error(request, f"Có lỗi xảy ra: {str(e)}")


    context = {
        'title': 'Thiết lập số dư đầu kỳ',

        # 1. Danh sách tài khoản kế toán (theo Thông tư 200 hoặc 133)
        'accounts': [
            {'code': '1111', 'name': 'Tiền mặt VNĐ', 'has_detal': False},
            {'code': '1121', 'name': 'Tiền gửi Ngân hàng VNĐ', 'has_detail': True},
            # ... lấy từ model Account
        ],

        # 2. Danh sách đối tượng công nợ
        'partners': [
            {'code': 'KH001', 'name': 'Công ty TNHH Giải pháp Phần mềm', 'type': 'Khách hàng'},
            {'code': 'NCC02', 'name': 'Tổng kho Nông sản miền Nam', 'type': 'Nhà cung cấp'},
        ],

        # 3. Danh sách tồn kho
        'inventory_items': [
            {'code': 'SP001', 'name': 'Sản phẩm A', 'unit': 'Cái', 'warehouse': 'Kho tổng'},
            {'code': 'NL04', 'name': 'Nguyên liệu thô', 'unit': 'Kg', 'warehouse': 'Kho phụ'},
        ],

        # 4. Danh sách tài sản/công cụ
        'assets': [
            {'code': 'TS001', 'name': 'Máy tính xách tay Dell', 'origin_price': 20000000},
        ]
    }

    return render(request, 'accounting/website/working_page.html', context)

def transaction_list(request):
    data = []
    return render(request, "accounting/website/transaction_list.html", {"transactions": data})


def transaction_detail(request, id):
    t = {}
    return render(request, "accounting/website/transaction_detail.html", {"t": t})


def journal_review(request):
    return render(request, "accounting/website/journal_review.html", {"journals": []})


def document_match(request):
    return render(request, "accounting/website/document_match.html", {"documents": []})


def register_list(request):
    return render(request, "accounting/website/register_list.html")

def register_detail(request, type):
    return render(request, "accounting/website/register_detail.html", {"rows": []})

# =============== SỔ KẾ TOÁN DOANH NGHIỆP ======
def to_number(val):
    if val is None:
        return None

    if isinstance(val, (int, float)):
        return val

    try:
        return float(str(val).replace(",", "").strip())
    except:

        return None

# Sổ Nhật ký chung (Nhật ký chung)
def api_generate_journal(request):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        data_list = payload if isinstance(payload, list) else payload.get('data', [])

        processed_rows = []
        stt = 1

        for row in data_list:
            entries = row.get("entries", [])

            if not entries:
                continue

            doc_no = row.get("number") or "CT"
            date = row.get("create_date")

            # 🔥 FIX: lấy đúng diễn giải
            desc = (
                row.get("product_name")
                or row.get("description")
                or "Hạch toán"
            )

            first_line = True

            for entry in entries:

                amount = to_number(entry.get("amount"))
                if amount is None:
                    continue

                row_data = {
                    "stt": stt if first_line else "",
                    "so_ct": doc_no if first_line else "",
                    "ngay_ct": date if first_line else "",
                    "dien_giai": desc if first_line else "",
                    "tai_khoan": entry.get("debit") or entry.get("credit"),
                    "ps_no": amount if entry.get("debit") else "",
                    "ps_co": amount if entry.get("credit") else ""
                }

                processed_rows.append(row_data)


                first_line = False

            stt += 1

        # =============================
        # 🔥 THÊM DÒNG CỘNG (QUAN TRỌNG)
        # =============================
        total_no = 0
        total_co = 0

        for r in processed_rows:
            if r.get("ps_no"):
                total_no += float(r["ps_no"])
            if r.get("ps_co"):
                total_co += float(r["ps_co"])

        processed_rows.append({
            "stt": "",
            "so_ct": "",
            "ngay_ct": "",
            "dien_giai": "Cộng số phát sinh",
            "tai_khoan": "",
            "ps_no": total_no,
            "ps_co": total_co
        })

        journal_entries = build_nhat_ky_chung(data_list)

        html = render_to_string(
            "accounting/website/reports/shared_diary/so_nhat_ky_chung.html",
            {"journal_entries": journal_entries}
        )

        return JsonResponse({
            "success": True,
            "html": html,
            "register_data": journal_entries
        })

    except Exception as e:

        return JsonResponse({"success": False, "error": str(e)}, status=500)

def clean_numeric(val):
    if val is None or val == "":
        return 0.0

    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    if not s:
        return 0.0

    # 👉 Nếu dạng US: 500,004.00
    if "," in s and "." in s:
        if s.index(",") < s.index("."):
            # US format
            s = s.replace(",", "")
        else:
            # VN format
            s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif "." in s:
        # giữ nguyên (US decimal)
        pass

    try:
        return float(s)
    except:
        return 0.0

def report_so_cai(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    try:
        body = json.loads(request.body)
        root_data = body.get("data", [])
    except Exception as e:
        return HttpResponseBadRequest(f"Invalid JSON: {str(e)}")

    if not root_data:
        return HttpResponseBadRequest("No data")

    normalized = []

    seen = set()

    for row in root_data:
        entries = row.get("entries", [])
        raw_date = row.get("create_date") or row.get("date")
        if not raw_date or not entries:
            continue

        debit_entries = [e for e in entries if e.get("debit")]
        credit_entries = [e for e in entries if e.get("credit")]

        # 1 Nợ - nhiều Có
        if len(debit_entries) == 1:
            d = debit_entries[0]
            d_acc = str(d.get("debit", "")).strip()
            if not d_acc:
                continue

            for c in credit_entries:
                c_acc = str(c.get("credit", "")).strip()
                if not c_acc:
                    continue

                amount = clean_numeric(c.get("amount"))
                if amount <= 0:
                    continue

                key = (str(raw_date), d_acc, c_acc, amount)

                if key in seen:
                    continue
                seen.add(key)  # ✅ PHẢI có dòng này

                normalized.append({
                    "date": str(raw_date),
                    "debit_account": d_acc,
                    "credit_account": c_acc,
                    "amount": amount,
                    "description": row.get("description") or "Hạch toán tự động"
                })

    if not normalized:
        return HttpResponseBadRequest("Dữ liệu hạch toán không hợp lệ hoặc thiếu tài khoản Nợ/Có")


    try:

        accounts = build_so_cai(normalized)

        return render(
            request,
            "accounting/website/reports/voucher_journal/so_cai.html",
            {
                "accounts": accounts,
                "report_name": "SỔ CÁI (S05-DN)",
            }
        )
    except Exception as e:

        traceback.print_exc()
        return JsonResponse({"error": f"Lỗi xử lý Sổ cái: {str(e)}"}, status=500)

def report_so_tien_gui(request):

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    try:
        body = json.loads(request.body.decode("utf-8"))
        raw_data = body.get("data", [])   # 🔥 FIX CHUẨN
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    try:

        result = build_so_tien_gui(raw_data)

        html = render_to_string(
            "accounting/website/reports/so_tien_gui_s08_dn.html",
            {
                "rows": result.get("rows", []),
                "generated_at": result.get("generated_at"),
                "report_name": result.get("report_name"),

                "account_number": result.get("account_number", ""),
                "bank_name": result.get("bank_name", ""),
            }
        )

        return JsonResponse({
            "success": True,
            "html": html,
            "register_data": result
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


def api_generate_s61_dn_register(request):

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Only POST allowed"}, status=405)

    try:

        payload = json.loads(request.body.decode("utf-8"))
        data_list = payload if isinstance(payload, list) else payload.get("data", [])

        if not data_list:
            return JsonResponse({
                "success": False,
                "error": "Không có dữ liệu"
            }, status=400)


        # =============================
        # 🔥 BUILD SỔ S61-DN
        # =============================
        journal_entries = build_s61_dn_register(data_list)

        # =============================
        # 🔥 RENDER HTML
        # =============================
        html = render_to_string(
            "accounting/website/reports/so_theo_doi_thue_gtgt.html",
            {
                "journal_entries": journal_entries
            }
        )

        return JsonResponse({
            "success": True,
            "html": html
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

# Sổ chi tiết vật liệ, dụng cụ, sản phẩm, hàng hóa
def api_generate_s10_dn_register(request):

    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "error": "Only POST allowed"
        }, status=405)

    try:

        # =====================================
        # 🔥 LOAD PAYLOAD
        # =====================================
        payload = json.loads(
            request.body.decode("utf-8")
        )

        # =====================================
        # 🔥 DATA LIST
        # =====================================
        data_list = (
            payload
            if isinstance(payload, list)
            else payload.get("data", [])
        )

        if not data_list:
            return JsonResponse({
                "success": False,
                "error": "Không có dữ liệu"
            }, status=400)

        # =====================================
        # 🔥 PRODUCT FILTER
        # =====================================
        product_filter = (
            payload.get("product")
            if isinstance(payload, dict)
            else None
        )

        # =====================================
        # 🔥 BUILD REGISTER
        # =====================================
        journal_entries = build_s10_dn_register(
            data_list=data_list,
            product_filter=product_filter
        )

        # =====================================
        # 🔥 RENDER HTML
        # =====================================
        html = render_to_string(
            "accounting/website/reports/so_chi_tiet_vl_dc_sp_hh.html",
            {
                "journal_entries": journal_entries,

                # 🔥 dropdown chọn hàng hóa
                "product_options": journal_entries.get(
                    "product_options",
                    []
                ),

                # 🔥 hàng đang chọn
                "selected_product": journal_entries.get(
                    "selected_product"
                )
            }
        )

        # =====================================
        # 🔥 RESPONSE
        # =====================================
        return JsonResponse({
            "success": True,

            "html": html,

            "register_data": journal_entries,

            "product_options": journal_entries.get(
                "product_options",
                []
            ),

            "selected_product": journal_entries.get(
                "selected_product"
            )
        })

    except Exception as e:

        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


# Sổ tổng hợp VL-DC-SP-HH
def api_generate_s11(request):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        data_list = payload.get("data", [])

        journal_entries = build_s11_dn_register(data_list)

        html = render_to_string(
            "accounting/website/reports/bang_tong_hop_vl_dc_sp_hh.html",
            {"journal_entries": journal_entries}
        )

        return JsonResponse({
            "success": True,
            "html": html,
            "register_data": journal_entries
        })

    except Exception as e:

        return JsonResponse({"success": False, "error": str(e)})

# Thẻ kho (Sổ kho)
def api_generate_s12(request):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        data_list = payload.get("data", [])
        product = payload.get("product")

        journal_entries = build_s12_dn_register(data_list, product)

        html = render_to_string(
            "accounting/website/reports/the_kho.html",
            {"journal_entries": journal_entries}
        )

        return JsonResponse({
            "success": True,
            "html": html,
            "register_data": journal_entries
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

# Bảng cân đối số phát sinh
def api_generate_s06(request):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        data_list = payload.get("data", [])

        journal_entries = build_s06_dn_register(data_list)

        html = render_to_string(
            "accounting/website/reports/bang_can_doi_so_phat_sinh.html",
            {"journal_entries": journal_entries}
        )

        return JsonResponse({
            "success": True,
            "html": html,
            "register_data": journal_entries
        })

    except Exception as e:

        return JsonResponse({"success": False, "error": str(e)})

# Sổ quỹ tiền mặt
def api_generate_s07(request):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        data_list = payload.get("data", [])

        journal_entries = build_s07_dn_register(data_list)

        html = render_to_string(
            "accounting/website/reports/so_quy_tien_mat.html",
            {
                "journal_entries": journal_entries,
            }
        )

        return JsonResponse({
            "success": True,
            "html": html,
            "register_data": journal_entries
        })

    except Exception as e:

        return JsonResponse({"success": False, "error": str(e)})

# Sổ kế toán chi tiết quỹ tiền mặt
def api_generate_s07a(request):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        data_list = payload.get("data", [])

        journal_entries = build_s07a_dn_register(data_list)

        html = render_to_string(
            "accounting/website/reports/so_chi_tiet_quy_tien_mat.html",
            {"journal_entries": journal_entries}
        )

        return JsonResponse({
            "success": True,
            "html": html,
            "register_data": journal_entries
        })

    except Exception as e:

        return JsonResponse({"success": False, "error": str(e)})

# Sổ chi tiết thanh toán Mua, Bán
def api_generate_s31(request):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))

        data_list = payload.get("data", [])
        account = payload.get("account", "131")
        partner = payload.get("partner")

        journal_entries = build_s31_dn_register(
            data_list,
            account,
            partner
        )

        # 🔥 chặn lỗi
        if "error" in journal_entries:
            return JsonResponse({
                "success": False,
                "error": journal_entries["error"]
            })

        html = render_to_string(
            "accounting/website/reports/so_chi_tiet_thanh_toan_mua_ban.html",
            {"journal_entries": journal_entries}
        )

        return JsonResponse({
            "success": True,
            "html": html,
            "register_data": journal_entries
        })

    except Exception as e:

        return JsonResponse({"success": False, "error": str(e)})

# Sổ chi tiết tiền vay
def api_generate_s34(request):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        data_list = payload.get("data", [])

        journal_entries = build_s34_dn_register(data_list)

        html = render_to_string(
            "accounting/website/reports/so_chi_tiet_tien_vay.html",
            {"journal_entries": journal_entries}
        )

        return JsonResponse({
            "success": True,
            "html": html,
            "register_data": journal_entries
        })

    except Exception as e:

        return JsonResponse({"success": False, "error": str(e)})

# Sổ chi tiết bán hàng
def api_generate_s35(request):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        data_list = payload.get("data", [])

        journal_entries = build_s35_dn_register(data_list)

        html = render_to_string(
            "accounting/website/reports/so_chi_tiet_ban_hang.html",
            {"journal_entries": journal_entries}
        )

        return JsonResponse({
            "success": True,
            "html": html,
            "register_data": journal_entries
        })

    except Exception as e:

        return JsonResponse({"success": False, "error": str(e)})

# Sổ chi phí sản xuất kinh doanh
def api_generate_s36(request):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        data_list = payload.get("data", [])

        journal_entries = build_s36_dn_register(data_list)

        html = render_to_string(
            "accounting/website/reports/so_chi_phi_sx_kd.html",
            {"journal_entries": journal_entries}
        )

        return JsonResponse({
            "success": True,
            "html": html,
            "register_data": journal_entries
        })

    except Exception as e:

        return JsonResponse({"success": False, "error": str(e)})

def api_generate_s01(request):
    """
    API render Sổ S01-DN (Nhật ký sổ cái)
    """

    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "error": "POST required"
        }, status=400)

    try:
        body = json.loads(request.body)
        raw_data = body.get("data", [])
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Invalid JSON: {str(e)}"
        }, status=400)

    # 🔹 1. Build register
    try:
        result = build_so1_dn_register(raw_data)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Build register failed: {str(e)}"
        }, status=500)

    # 🔹 2. Render template
    try:

        html = render_to_string(
            "accounting/website/reports/ledger_journal/nhat_ky_so_cai.html",
            {
                "report_name": result.get("report_name"),
                "rows": result.get("rows", []),
                "total_no": result.get("total_no", 0),
                "total_co": result.get("total_co", 0),
                "generated_at": result.get("generated_at"),
            }
        )
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Render template failed: {str(e)}"
        }, status=500)

    # 🔹 3. Return đúng format cho JS
    return JsonResponse({
        "success": True,
        "html": html,
        "count": len(result.get("rows", []))
    })

# Thẻ tính giá thành SP, DV
def api_generate_s37(request):

    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "error": "POST required"
        }, status=400)

    # 🔹 1. Parse JSON
    try:
        body = json.loads(request.body)

        raw_data = body.get("data", [])
        product = body.get("product_name", "")
        month = body.get("month")
        year = body.get("year")

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Invalid JSON: {str(e)}"
        }, status=400)

    # 🔹 2. Build register (S37)
    try:
        data = build_s37_dn_register(
            data_list=raw_data,  # ✅ đúng tên param
            product_name=product,
            month=month,
            year=year
        )
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Build register failed: {str(e)}"
        }, status=500)

    # 🔹 3. Render HTML
    try:
        html = render_to_string(
            "accounting/website/reports/the_tinh_gia_thanh_sp_dv.html",
            {
                "data": data,
                "report_name": data.get("report_name")
            }
        )
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Render template failed: {str(e)}"
        }, status=500)

    # 🔹 4. Response chuẩn hệ thống bạn
    return JsonResponse({
        "success": True,
        "data": data,
        "html": html,

    })

# Sổ chi tiết các tài khoản
def api_generate_s38(request):

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=400)

    try:
        body = json.loads(request.body)

        raw_data = body.get("data", [])
        account = body.get("account")


    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

    try:
        data = build_s38_dn_register(
            data_list=raw_data,
            account_filter=account
        )

        journal_entries = build_s38_dn_register(
            data_list=raw_data,
            account_filter=account
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

    html = render_to_string(
        "accounting/website/reports/so_chi_tiet_cac_tai_khoan.html",
        {"data": data}
    )

    return JsonResponse({
        "success": True,
        "data": data,
        "html": html,
        "register_data": journal_entries
    })

# Sổ theo dõi chi tiết các khoản ĐT của Cty Liên doanh
def api_generate_s41a(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=400)

    try:
        body = json.loads(request.body)
        data = body.get("data", [])

        report_data = build_s41a_dn_register(data)

        html = render_to_string(
            "accounting/website/reports/so_theo_doi_dau_tu_vao_cty_lien_doanh.html",
            {
                "data": report_data,
                "report_name": "SỔ THEO DÕI VỐN ĐẦU TƯ VÀO CÔNG TY LIÊN DOANH (S41a-DN"
            }
        )

        return JsonResponse({
            "success": True,
            "html": html
        })

    except Exception as e:

        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

# Sổ theo dõi chi tiết các khoản ĐT của Cty Liên kết
def api_generate_s42a(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=400)

    try:
        body = json.loads(request.body)
        data = body.get("data", [])

        report_data = build_s41a_dn_register(data)

        html = render_to_string(
            "accounting/website/reports/so_theo_doi_dau_tu_vao_cty_lien_ket.html",
            {
                "data": report_data,
                "report_name": "SỔ THEO DÕI VỐN ĐẦU TƯ VÀO CÔNG TY LIÊN DOANH (S42a-DN"
            }
        )

        return JsonResponse({
            "success": True,
            "html": html
        })

    except Exception as e:

        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


