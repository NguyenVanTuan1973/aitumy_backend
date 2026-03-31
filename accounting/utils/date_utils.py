# accounting/utils/date_utils.py

from datetime import datetime, timedelta


def excel_date_to_date(excel_serial):
    """
    Convert Excel serial date to Python datetime
    Example: 46082 -> 2026-03-01
    """
    if not excel_serial:
        return None

    base_date = datetime(1899, 12, 30)
    return base_date + timedelta(days=int(excel_serial))