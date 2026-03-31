from .hkd_sheet_service_show import HKDSheetServiceShow


class HKDProSheetServiceShow(HKDSheetServiceShow):

    def get_data(self):

        data = super().get_data()

        data["dashboard"] = {
            "cashflow": data["overview"]["income"] - data["overview"]["expense"]
        }

        return data