def preview_ocr(pdf_path):
    import pytesseract
    from pdf2image import convert_from_path
    import os

    pages = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
    if not pages:
        return ""

    return pytesseract.image_to_string(pages[0], lang="vie+eng")
