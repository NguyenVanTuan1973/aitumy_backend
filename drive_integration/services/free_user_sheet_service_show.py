from datetime import date
from ..utils.period_utils import get_current_year, get_period_range
from .google_sheet_get_data_service import GoogleSheetGetDataService
from .sheet_row_mapper import map_documents_to_sheet_rows, map_sheet_rows_to_documents


class FreeUserSheetServiceShow:

    def __init__(self, *, user, params, spreadsheet_id: str):
        self.user = user
        self.params = params

        self.sheet_service = GoogleSheetGetDataService(
            user=user,
            spreadsheet_id=spreadsheet_id,
        )

    # =====================================================
    # ENTRY POINT
    # =====================================================
    def get_data(self):
        mode = self.params.get("mode", "overview")

        if mode == "filter":
            return self._get_data_by_period()

        return self._get_overview()

    # =====================================================
    # OVERVIEW
    # =====================================================
    def _get_overview(self):
        year = get_current_year()

        raw_rows = self.sheet_service.read_overview()
        rows = map_sheet_rows_to_documents(raw_rows)

        return {
            "mode": "overview",
            "year": year,
            "total": self._calculate_total(rows),
            "rows": rows,
        }

    # =====================================================
    # FILTER BY PERIOD
    # =====================================================
    def _get_data_by_period(self):
        period_type = self.params.get("period_type")
        anchor = self._build_anchor_date()

        start_date, end_date = get_period_range(period_type, anchor)

        raw_rows = self.sheet_service.read_by_period(
            start_date=start_date,
            end_date=end_date,
        )

        rows = map_documents_to_sheet_rows(raw_rows)

        return {
            "mode": "filter",
            "filter": {
                "period_type": period_type,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "total": self._calculate_total(rows),
            "rows": rows,
        }

    # =====================================================
    # HELPERS
    # =====================================================
    def _build_anchor_date(self):
        period_type = self.params.get("period_type")
        year = int(self.params.get("year"))

        if period_type == "month":
            month = int(self.params.get("month"))
            return date(year, month, 1)

        if period_type == "quarter":
            quarter = int(self.params.get("quarter"))
            start_month = (quarter - 1) * 3 + 1
            return date(year, start_month, 1)

        if period_type == "year":
            return date(year, 1, 1)

        raise ValueError("INVALID_PERIOD_TYPE")

    def _calculate_total(self, rows):
        return sum(r.get("amount", 0) for r in rows)

