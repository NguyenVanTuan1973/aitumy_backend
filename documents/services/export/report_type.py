from enum import Enum


class ReportType(str, Enum):

    # INDIVIDUAL
    INDIVIDUAL_INCOME = "INDIVIDUAL_INCOME"
    INDIVIDUAL_EXPENSE = "INDIVIDUAL_EXPENSE"

    # HKD
    HKD_INCOME = "HKD_INCOME"
    HKD_EXPENSE = "HKD_EXPENSE"

    # 🔥 ACCOUNTING REGISTER
    ACCOUNTING_REGISTER = "ACCOUNTING_REGISTER"

    # ENTERPRISE
    ENTERPRISE_BALANCE = "ENTERPRISE_BALANCE"

    @classmethod
    def values(cls):
        return [e.value for e in cls]