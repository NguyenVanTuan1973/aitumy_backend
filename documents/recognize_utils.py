import os
import re
import unidecode

import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageOps
import cv2
import numpy as np

from django.conf import settings
from documents.models import FormTemplate
from .extract_utils import generate_pdf_thumbnail, generate_image_thumbnail


try:
    from unidecode import unidecode
except Exception:
    # nếu chưa cài package, thông báo hướng dẫn (pip install Unidecode)
    def unidecode(s: str) -> str:
        return s  # fallback: trả về nguyên gốc nếu chưa cài

# =========================
# 1. OCR – TRÍCH XUẤT VĂN BẢN
# =========================

def extract_text_auto(file_path: str) -> str:

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
        if len(text.strip()) < 20:  # PDF scan → dùng OCR
            text = ocr_pdf(file_path)
        return text

    elif ext in [".jpg", ".jpeg", ".png"]:
        return ocr_image_advanced(file_path)

    return ""

def extract_text_from_pdf(pdf_path: str) -> str:
    """Trích xuất text từ PDF có text-readable."""
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text() or ""
    doc.close()
    return text

def ocr_pdf(pdf_path: str) -> str:
    """OCR cho toàn bộ PDF scan."""
    text = ""
    pages = convert_from_path(pdf_path, dpi=250)
    for img in pages:
        text += pytesseract.image_to_string(img, lang="vie+eng")
    return text

def ocr_image_advanced(image_path: str) -> str:

    try:
        # Mở ảnh
        img = Image.open(image_path).convert("RGB")

        # Resize ảnh nếu quá nhỏ
        max_width = 1600
        if img.width < max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)

            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)


        # Chuyển sang grayscale
        img_gray = ImageOps.grayscale(img)

        # Tăng contrast
        enhancer = ImageEnhance.Contrast(img_gray)
        img_contrast = enhancer.enhance(2.0)

        # Threshold (binarization) để chữ nổi bật
        img_np = np.array(img_contrast)
        _, img_thresh = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        img_final = Image.fromarray(img_thresh)

        # OCR
        text = pytesseract.image_to_string(img_final, lang="vie+eng")


        # Nếu vẫn trống, thử đọc ảnh gốc như fallback
        if not text.strip():
            text = pytesseract.image_to_string(img, lang="vie+eng")


        return text

    except Exception as e:
        print("🔥 OCR IMAGE ERROR:", e)
        return ""

# =========================
# 2. NHẬN DIỆN MẪU CHỨNG TỪ
# =========================

def detect_form_template(ocr_text: str):
    """
    Nhận diện FormTemplate tốt hơn:
      - normalize (lower + remove accents)
      - ưu tiên match title (nếu có)
      - match mã mẫu (code) đã normalize (bỏ khoảng trắng)
      - match keywords (bỏ keyword ngắn <3)
      - trả về template object + score + folder (None nếu chưa có)
    """
    if not ocr_text:
        return {"template": None, "score": 0, "folder": "khac"}

    # chuẩn hoá OCR text
    try:
        text_norm = unidecode(ocr_text.lower())
    except Exception:
        text_norm = ocr_text.lower()

    # xóa nhiều khoảng trắng, ký tự lạ thừa
    text_norm = re.sub(r'\s+', ' ', text_norm).strip()

    best_template = None
    best_score = 0

    for temp in FormTemplate.objects.filter(is_active=True):
        score = 0

        # Lấy title từ model nếu có, fallback dùng name hoặc example_text
        title_source = None
        if hasattr(temp, "title") and temp.title:
            title_source = temp.title
        elif hasattr(temp, "name") and temp.name:
            title_source = temp.name
        elif hasattr(temp, "example_text") and temp.example_text:
            # dùng một đoạn ngắn làm title fallback
            title_source = (temp.example_text[:120] or "").splitlines()[0]
        else:
            title_source = None

        # 1) Title match (ưu tiên, trọng số lớn)
        if title_source:
            try:
                title_norm = unidecode(title_source.lower())
            except Exception:
                title_norm = title_source.lower()
            title_norm = re.sub(r'\s+', ' ', title_norm).strip()

            # match whole word (word boundary)
            if re.search(rf"\b{re.escape(title_norm)}\b", text_norm):
                score += 60

        # 2) Match code (01-TT, 02-TT, ...)
        if getattr(temp, "code", None):
            code_norm = str(temp.code).lower().replace(" ", "").replace("–", "-").replace("—", "-")
            text_compact = re.sub(r'\s+', '', text_norm)
            if code_norm and code_norm in text_compact:
                score += 20

        # 3) Keywords (loại bỏ từ quá ngắn)
        if getattr(temp, "keywords", None):
            for kw in str(temp.keywords).split(","):
                kw = kw.strip()
                if not kw:
                    continue
                try:
                    kw_norm = unidecode(kw.lower())
                except Exception:
                    kw_norm = kw.lower()
                kw_norm = re.sub(r'\s+', ' ', kw_norm).strip()

                # bỏ keyword 1-2 ký tự (quá chung)
                if len(kw_norm) < 3:
                    continue

                # exact substring match (đã normalized)
                if kw_norm in text_norm:
                    score += 10

                # nếu không exact, thử split thành từ và match từng token
                else:
                    for token in kw_norm.split():
                        if len(token) >= 3 and token in text_norm:
                            score += 5
                            break

        # cập nhật best
        if score > best_score:
            best_score = score
            best_template = temp

    if best_template:
        folder = getattr(best_template, "drive_group_path", None) if hasattr(best_template, "drive_group_path") else None
        return {"template": best_template, "score": best_score, "folder": folder}

    return {"template": None, "score": 0, "folder": "khac"}

# =========================
# 3. TRÍCH XUẤT METADATA CƠ BẢN
# =========================

def extract_basic_metadata(text: str) -> dict:
    metadata = {}

    # Số chứng từ / Số hóa đơn
    m_so_ct = re.search(r"(Số[:\s]*|No[:\s]*)([A-Za-z0-9/.\-]+)", text, re.I)
    if m_so_ct:
        metadata["reference_number"] = m_so_ct.group(2).strip()

    # Ngày chứng từ
    m_date = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
    if m_date:
        metadata["date"] = m_date.group(1)

    # Tiêu đề / Tên chứng từ
    first_line = text.strip().split("\n")[0]
    if len(first_line) < 80:
        metadata["title"] = first_line.strip()

    return metadata

# =========================
# 4. HÀM CHÍNH DÙNG TRONG API
# =========================

def recognize_document(file_path) -> dict:
    """
    Nhận diện chứng từ từ FILE (PDF hoặc Ảnh)
    - OCR
    - Nhận diện mẫu
    - Lấy metadata
    - Tạo thumbnail phù hợp
    """
    file_path = str(file_path)  # chắc chắn là string

    # 1) OCR tự động
    ocr_text = extract_text_auto(file_path)

    # 2) Nhận diện mẫu
    template_info = detect_form_template(ocr_text)
    template = template_info["template"]
    folder = template_info["folder"]
    template_name = template.name if template else "Không xác định"

    # 3) Metadata
    meta = extract_basic_metadata(ocr_text)

    # 4) Tạo thumbnail
    ext = os.path.splitext(file_path)[1].lower()

    thumbnail_rel_path = None

    try:
        if ext == ".pdf":
            thumbnail_rel_path = generate_pdf_thumbnail(file_path)
        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
            thumbnail_rel_path = generate_image_thumbnail(file_path)
    except Exception as e:
        thumbnail_rel_path = None

    return {
        "ocr_text": ocr_text,
        "template": template_name,
        "storage_folder": folder,
        "metadata": meta,
        "form_code": template.code if template else None,
        "score": template_info["score"],
        "thumbnail_url": thumbnail_rel_path,  # đã là /media/...
    }

