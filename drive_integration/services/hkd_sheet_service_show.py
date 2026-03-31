from .base_sheet_service import BaseSheetService



class HKDSheetServiceShow(BaseSheetService):

    def get_data(self):

        records = self.load_sheet_rows(sheet_name="data_source")

        rows = []
        set_ids = set()

        # ===============================
        # 1️⃣ BUILD ROWS
        # ===============================
        for r in records:

            job_code = r.get("job_code")

            if job_code == "income":
                doc_type = "thu"

            elif job_code == "expense":
                doc_type = "chi"

            else:
                continue

            set_id = r.get("set_id")

            if set_id:
                set_ids.add(set_id)

            rows.append({
                "doc_date": r.get("doc_date"),
                "doc_content": r.get("doc_content"),
                "total_amount": float(r.get("total_amount") or 0),
                "doc_type": doc_type,
                "payment_type": r.get("payment_type"),
                "accounting_code": r.get("accounting_code"),
                "set_id": set_id,
            })

        # ===============================
        # 2️⃣ LOAD METADATA SHEET
        # ===============================
        metadata_rows = self.load_sheet_rows(
            sheet_name="documents_metadata"
        )

        doc_map = {}

        for r in metadata_rows:

            set_id = r.get("set_id")
            file_id = r.get("file_drive_id")

            if not set_id or not file_id:
                continue

            url = f"https://drive.google.com/file/d/{file_id}/view"

            doc_map.setdefault(set_id, []).append(url)

        # ===============================
        # 3️⃣ ATTACH document_url
        # ===============================
        for r in rows:

            set_id = r.get("set_id")

            if not set_id:
                r["document_url"] = None
                continue

            urls = doc_map.get(set_id)

            r["document_url"] = urls[0] if urls else None

        return {
            "rows": rows
        }

