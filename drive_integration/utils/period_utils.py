from datetime import date
import calendar
from datetime import datetime
from dataclasses import dataclass



def get_current_year() -> int:
    """
    Trả về năm hiện tại (YYYY)
    Dùng cho tổng quan, filter mặc định
    """
    return datetime.now().year

def get_period_range(period_type: str, anchor: date):
    """
    Return (start_date, end_date)
    """

    if period_type == "month":
        start = anchor.replace(day=1)
        last_day = calendar.monthrange(anchor.year, anchor.month)[1]
        end = anchor.replace(day=last_day)

    elif period_type == "quarter":
        quarter = (anchor.month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2

        start = date(anchor.year, start_month, 1)
        last_day = calendar.monthrange(anchor.year, end_month)[1]
        end = date(anchor.year, end_month, last_day)

    elif period_type == "year":
        start = date(anchor.year, 1, 1)
        end = date(anchor.year, 12, 31)

    else:
        raise ValueError("Invalid period_type")

    return start, end

# ==================================================
# 🔥 PERIOD FILTER OBJECT (DÙNG CHO SERVICE / API)
# ==================================================
@dataclass
class PeriodFilter:
    period_type: str
    start_date: date
    end_date: date

    def to_dict(self):
        return {
            "period_type": self.period_type,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }