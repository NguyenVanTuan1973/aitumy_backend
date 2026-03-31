import os
import re
from PIL import Image, ImageOps
from datetime import datetime
from collections import Counter
import pdfplumber
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from django.conf import settings
import uuid
from .models import FormTemplate

import logging
logger = logging.getLogger(__name__)

# ============== CẤU HÌNH OCR ==============
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ['TESSDATA_PREFIX'] = r"C:\Program Files\Tesseract-OCR\tessdata"
POPPLER_PATH = r"C:\poppler-25.07.0\Library\bin"

THUMB_DIR = os.path.join(settings.MEDIA_ROOT, "documents", "thumbnails")
os.makedirs(THUMB_DIR, exist_ok=True)

# ============================================================
# 🧠 1️⃣ TRÍCH XUẤT TEXT CƠ BẢN
# ============================================================

def extract_from_pdf(file_path):
    """Trích xuất text từ PDF bằng pdfplumber."""
    text_content = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_content += f"\n--- Trang {i + 1} ---\n"
                    text_content += page_text


    except Exception as e:

        text_content = None

    return text_content

def ocr_extract(pdf_path: str) -> str:
    """Trích xuất text từ PDF (chưa OCR)."""
    extracted_text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page_num, page in enumerate(doc, start=1):
                extracted_text += f"\n\n=== PAGE {page_num} ===\n{page.get_text('text').strip()}"
        if not extracted_text.strip():
            extracted_text = "⚠️ PDF không có lớp văn bản."
    except Exception as e:
        extracted_text = f"❌ Lỗi khi đọc file PDF: {e}"
    return extracted_text

def extract_text_auto(pdf_path: str) -> str:
    """Tự động chọn giữa PyMuPDF hoặc OCR (Tesseract)."""
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text("text").strip() + "\n"
        if text.strip():

            return text

    except Exception as e:
        print(f"❌ Lỗi PyMuPDF: {e}")

    try:
        pages = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1, poppler_path=POPPLER_PATH)
        if pages:
            text = pytesseract.image_to_string(pages[0], lang="vie+eng")
    except Exception as e:
        print(f"❌ Lỗi OCR fallback: {e}")

    return text

# ============================================================
# 📊 2️⃣ PHÂN TÍCH THÔNG TIN CHỨNG TỪ
# ============================================================

def parse_invoice_text(text: str) -> dict:
    """Phân tích thông tin cơ bản từ text PDF."""
    result = {}

    m_tax = re.search(r'\b(\d{10,14})\b', text)
    if m_tax:
        result['tax_code'] = m_tax.group(1)

    m_no = re.search(r'(?:Số[:\-]?\s*|H\.?D\.?|Hóa đơn[:\-]?)\s*([A-Za-z0-9\-\/]+)', text, re.I)
    if m_no:
        result['doc_no'] = m_no.group(1)

    m_date = re.search(r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', text)
    if m_date:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
            try:
                result['doc_date'] = datetime.strptime(m_date.group(1), fmt).date()
                break
            except Exception:
                continue

    m_total = re.search(r'(?:Tổng cộng|Thành tiền)[^0-9]*([\d\.,]+)', text, re.I)
    if m_total:
        raw = m_total.group(1)
        raw_clean = raw.replace('.', '').replace(',', '.')
        try:
            result['total_amount'] = float(raw_clean)
        except Exception:
            pass

    return result

def extract_and_parse(file_path: str) -> dict:
    """Hàm tổng hợp: OCR + parse cơ bản."""
    ocr_text = extract_text_auto(file_path)
    fields = parse_invoice_text(ocr_text)

    log = {
        "status": "ok" if ocr_text else "empty",
        "notes": "Trích xuất thành công.",
        "fields_detected": list(fields.keys())
    }
    return {"ocr_text": ocr_text, "fields": fields, "log": log}

# ============================================================
# 🧩 3️⃣ NHẬN DẠNG MẪU (FormTemplate)
# ============================================================

def identify_form_template(text: str):
    """Nhận diện mẫu biểu (FormTemplate) dựa trên keywords."""
    templates = FormTemplate.objects.filter(is_active=True)
    best_match, best_score = None, 0.0

    for t in templates:
        if not t.keywords:
            continue
        keywords = [kw.strip().lower() for kw in t.keywords.split(",") if kw.strip()]
        match_count = sum(1 for kw in keywords if kw in text.lower())
        score = match_count / len(keywords)

        if score > best_score and score >= (t.confidence_threshold or 0.7):
            best_match, best_score = t, score

    return best_match, round(best_score, 3)

def extract_fields_from_structure(text: str, form_template: FormTemplate):
    """Trích xuất các trường động từ structure_json của mẫu."""
    if not form_template or not form_template.structure_json:
        return {}

    structure = form_template.structure_json
    fields = {}

    # Cấu trúc có thể là {"fields": [{label, regex}, ...]} hoặc dict[field_name] = regex
    if isinstance(structure, dict) and "fields" in structure:
        for field in structure["fields"]:
            label = field.get("label")
            pattern = field.get("regex")
            try:
                match = re.search(pattern, text)
                if match:
                    fields[label] = match.group(1) if match.groups() else match.group(0)
            except Exception as e:
                print(f"⚠️ Regex lỗi ở {label}: {e}")
    else:
        for key, cfg in structure.items():
            pattern = cfg.get("regex") if isinstance(cfg, dict) else cfg
            try:
                match = re.search(pattern, text)
                if match:
                    fields[key] = match.group(1) if match.groups() else match.group(0)
            except Exception as e:
                print(f"⚠️ Regex lỗi ở {key}: {e}")

    return fields

# ============================================================
# 🧱 4️⃣ HỖ TRỢ ADMIN: TRÍCH XUẤT MẪU FORM
# ============================================================

ACCOUNTING_BOOST = {
    "phiếu", "bảng", "biên bản", "hóa đơn",
    "thu", "chi", "tổng tiền", "số tiền",
    "ngày", "ký", "họ tên"
}

def extract_keywords(text: str, top_n=30) -> str:
    stopwords = {...}
    words = re.findall(r'\b[\wÀ-ỹ]{3,}\b', text.lower())

    scored = Counter()
    for i, w in enumerate(words):
        if w in stopwords:
            continue
        score = 1
        if w in ACCOUNTING_BOOST:
            score += 2
        if i < 50:  # xuất hiện sớm
            score += 1
        scored[w] += score

    common = [w for w, _ in scored.most_common(top_n)]
    return ", ".join(common)

def generate_structure_template(text: str) -> dict:
    fields = []

    if re.search(r"số\s+(phiếu|chứng từ)", text, re.I):
        fields.append({
            "key": "receipt_no",
            "label": "Số phiếu",
            "type": "text",
            "required": True,
            "patterns": [r"Số\s+(?:phiếu|chứng từ)[:\s]*([A-Z0-9\-]+)"],
            "confidence_weight": 1.0
        })

    if re.search(r"ngày\s+\d{1,2}", text.lower()):
        fields.append({
            "key": "receipt_date",
            "label": "Ngày chứng từ",
            "type": "date",
            "required": True,
            "patterns": [r"Ngày[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"]
        })

    if re.search(r"(tổng cộng|số tiền)", text.lower()):
        fields.append({
            "key": "amount",
            "label": "Số tiền",
            "type": "money",
            "required": True,
            "patterns": [r"(?:Tổng cộng|Số tiền)[^\d]*([\d\.,]+)"]
        })

    return {
        "fields": fields,
        "notes": "Cấu trúc sinh tự động – cần Admin xác nhận"
    }

def extract_form_template_data(file_path: str) -> dict:
    """
    🎯 Trích xuất dữ liệu FormTemplate cho Django Admin.
    - OCR file PDF/DOCX
    - Lọc sạch text
    - Gợi ý keywords
    - Sinh structure_json cơ bản
    - Trả về log cho Admin hiển thị
    """

    try:
        text = extract_text_auto(file_path) or ""
    except Exception as e:
        return {
            "example_text": "",
            "keywords": "",
            "structure_json": {},
            "log": f"Lỗi OCR: {e}"
        }

    text = text.strip()

    if not text:
        return {
            "example_text": "",
            "keywords": "",
            "structure_json": {},
            "log": "❌ Không thể trích xuất nội dung từ file."
        }

    # ============================
    # 1) CLEAN TEXT
    # ============================
    text_cleaned = re.sub(r"\n{3,}", "\n\n", text)
    text_cleaned = text_cleaned.strip()

    # ============================
    # 2) EXTRACT KEYWORDS
    # ============================
    try:
        keywords = extract_keywords(text_cleaned)
    except Exception:
        keywords = ""

    # ============================
    # 3) GENERATE STRUCTURE TEMPLATE
    # ============================
    try:
        structure = generate_structure_template(text_cleaned)
    except Exception:
        structure = {}

    # ============================
    # 4) GỢI Ý TITLE
    # ============================
    title_guess = ""
    first_lines = text_cleaned.split("\n")[:6]

    for line in first_lines:
        line_clean = line.strip()
        if len(line_clean) >= 6 and any(x in line_clean.upper() for x in ["PHIẾU", "BẢNG", "HÓA ĐƠN", "BIÊN BẢN"]):
            title_guess = line_clean.upper()
            break

    # fallback title
    if not title_guess:
        title_guess = first_lines[0].strip().upper()

    # ============================
    # 5) RETURN SAFE STRUCTURE_JSON
    # (Không dùng json.dumps vì JSONField cần object)
    # ============================
    return {
        "example_text": text_cleaned[:5000],   # Giới hạn cho admin
        "keywords": keywords,
        "title_guess": title_guess,
        "structure_json": structure,           # JSONField -> phải trả dict
        "field_candidates": [
            {"key": "receipt_no", "matched": True},
            {"key": "amount", "matched": True}
        ],
        "log": "✅ Trích xuất thành công & sinh dữ liệu mẫu.",

    }

def generate_pdf_thumbnail(pdf_path, filename=None):
    try:
        pages = convert_from_path(
            pdf_path,
            dpi=150,
            first_page=1,
            last_page=1,
            poppler_path=POPPLER_PATH
        )
        if not pages:
            return None

        thumb_dir = os.path.join(settings.MEDIA_ROOT, "documents", "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)

        base_name = filename or os.path.basename(pdf_path)
        name_only = os.path.splitext(base_name)[0]
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name_only)[:50]
        unique_suffix = uuid.uuid4().hex[:6]
        thumb_name = f"{safe_name}_{unique_suffix}.jpg"
        thumb_path = os.path.join(thumb_dir, thumb_name)

        page = ImageOps.exif_transpose(pages[0])
        page.thumbnail((800, 1100))
        page.save(thumb_path, "JPEG", quality=85)

        return f"/media/documents/thumbnails/{thumb_name}"

    except Exception as e:
        logger.exception("❌ generate_pdf_thumbnail failed")
        return None

def generate_image_thumbnail(image_path):
    try:
        thumb_dir = os.path.join(settings.MEDIA_ROOT, "documents", "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)

        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        img.thumbnail((800, 1100))

        base_name = os.path.basename(image_path)
        name_only = os.path.splitext(base_name)[0]
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name_only)[:50]
        unique_suffix = uuid.uuid4().hex[:6]
        thumb_name = f"{safe_name}_{unique_suffix}.jpg"
        thumb_path = os.path.join(thumb_dir, thumb_name)

        img.save(thumb_path, "JPEG", quality=85)

        return f"/media/documents/thumbnails/{thumb_name}"

    except Exception:
        logger.exception("❌ generate_image_thumbnail failed")
        return None






