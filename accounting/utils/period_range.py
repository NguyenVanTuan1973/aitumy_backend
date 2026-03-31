from datetime import date


def build_period_range(period_type, year, month=None, quarter=None):

    if period_type == "month":

        start = date(year, int(month), 1)

        if month == 12:
            end = date(year, 12, 31)
        else:
            end = date(year, int(month) + 1, 1)

    elif period_type == "quarter":

        start_month = (int(quarter) - 1) * 3 + 1
        end_month = start_month + 2

        start = date(year, start_month, 1)
        end = date(year, end_month, 28)

    else:

        start = date(year, 1, 1)
        end = date(year, 12, 31)

    return start, end