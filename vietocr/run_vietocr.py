import pytesseract
from PIL import Image
import os

# ⚙️ Đường dẫn tesseract.exe (bạn cần đúng đường dẫn)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text(image_path):
    if not os.path.exists(image_path):
        return f"❌ File không tồn tại: {image_path}"

    # Mở ảnh
    img = Image.open(image_path)

    # ⚡ Cấu hình tối ưu cho tiếng Việt
    custom_config = (
        "--oem 1 --psm 6 -l vie --dpi 300 "
        "--tessdata-dir 'C:\\Program Files\\Tesseract-OCR\\tessdata' "
        "--user-words D:\\aitumy\\aitumy_backend\\vietocr\\viet_words.txt "
        "--user-patterns D:\\aitumy\\aitumy_backend\\vietocr\\viet_patterns.txt"
    )

    # Nhận dạng
    text = pytesseract.image_to_string(img, config=custom_config)

    print(f"✅ OCR hoàn tất ({len(text)} ký tự).")
    return text

if __name__ == "__main__":
    test_img = r"D:\aitumy\aitumy_backend\media\documents\image\templates\image\200-2014-TT-BTC_01b-LĐTL_preview.jpg"
    print(extract_text(test_img))
