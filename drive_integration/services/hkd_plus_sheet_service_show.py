from .hkd_sheet_service_show import HKDSheetServiceShow


class HKDPlusSheetServiceShow(HKDSheetServiceShow):

    def get_data(self):

        data = super().get_data()

        rows = data.get("rows", [])

        income_count = 0
        expense_count = 0

        for r in rows:

            if r.get("doc_type") == "thu":
                income_count += 1

            elif r.get("doc_type") == "chi":
                expense_count += 1

        # thêm analytics
        data["analytics"] = {
            "total_income_docs": income_count,
            "total_expense_docs": expense_count,
        }

        return data