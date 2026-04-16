def map_register_rows(sheet_rows):

    rows = []
    total = 0

    for r in sheet_rows:

        amount = float(r["total_amount"] or 0)

        rows.append({
            "date": r["doc_date"],
            "description": r["doc_content"],
            "amount": amount
        })

        total += amount

    return rows, total