from datetime import datetime
from decimal import Decimal


def map_document_to_sheet_row(doc):
    """
    Chuyển DocumentMetadata → List value append vào Sheet
    """

    doc_type = doc.doc_type or "khac"

    if doc_type == "ban_thu":
        return "ban_thu", [
            doc.issue_date.strftime("%Y-%m-%d") if doc.issue_date else "",
            doc.document_no or "",
            doc.partner_name or "",
            doc.description or "",
            doc.amount or 0,
            doc.tax_amount or 0,
            doc.total_amount or 0,
            doc.payment_method or "",
            doc.drive_file_url or "",
        ]

    if doc_type == "mua_chi":
        return "mua_chi", [
            doc.issue_date.strftime("%Y-%m-%d") if doc.issue_date else "",
            doc.document_no or "",
            doc.partner_name or "",
            doc.description or "",
            doc.amount or 0,
            doc.tax_amount or 0,
            doc.total_amount or 0,
            doc.payment_method or "",
            doc.drive_file_url or "",
        ]

    if doc_type == "hoa_don":
        return "hoa_don", [
            doc.issue_date.strftime("%Y-%m-%d") if doc.issue_date else "",
            doc.invoice_no or "",
            doc.invoice_type or "",
            doc.partner_name or "",
            doc.amount or 0,
            doc.tax_amount or 0,
            doc.total_amount or 0,
            doc.status or "",
            doc.drive_file_url or "",
        ]

    # fallback
    return "bao_cao", [
        doc_type,
        datetime.now().strftime("%Y-%m-%d"),
        doc.total_amount or 0,
        doc.description or "",
    ]

def map_documents_to_sheet_rows(docs):
    """
    Chuyển list Document → list sheet rows
    """
    result = []

    for doc in docs:
        sheet_type, row = map_document_to_sheet_row(doc)
        result.append({
            "type": sheet_type,
            "row": row,
        })

    return result

def map_sheet_rows_to_documents(rows):
    """
    Google Sheet row (list) → FE document object
    """
    result = []
    for item in rows:
        sheet = item["sheet_name"]   # ✅ ĐÚNG KEY
        r = item["row"]

        if len(r) < 5:
            continue

        result.append({
            "date": r[0],
            "content": r[1],
            "amount": Decimal(r[2]) if r[2] else 0,
            "payment_method": r[3],
            "created_date": r[4],
            "doc_type": "thu" if sheet == "so_doanh_thu" else "chi",
        })

    # for r in rows:
    #     if len(r) < 5:
    #         continue
    #
    #     result.append({
    #         "date": r[0],
    #         "content": r[1],
    #         "amount": Decimal(r[2]) if r[2] else 0,
    #         "payment_method": r[3],
    #         "created_date": r[4],
    #         "doc_type": "thu" if sheet == "so_doanh_thu" else "chi",
    #     })

    return result




