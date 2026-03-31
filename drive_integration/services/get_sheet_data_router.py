from .hkd_sheet_service_show import HKDSheetServiceShow
from .hkd_plus_sheet_service_show import HKDPlusSheetServiceShow
from .hkd_pro_sheet_service_show import HKDProSheetServiceShow
from .free_user_sheet_service_show import FreeUserSheetServiceShow


def get_user_plan_code(user):
    """
    Lấy plan code của user thông qua organization
    """

    member = (
        user.memberships
        .select_related("organization__subscription__plan")
        .first()
    )

    if not member:
        return "free"

    subscription = getattr(member.organization, "subscription", None)

    if not subscription:
        return "free"

    return subscription.plan.code

def get_sheet_data_by_user(user, params, spreadsheet_id):

    plan_code = get_user_plan_code(user)

    # ===== ENTERPRISE =====
    if plan_code == "enterprise":
        raise NotImplementedError("Enterprise chưa làm")

    # ===== HKD PRO =====
    if plan_code == "hkd_pro":

        return HKDProSheetServiceShow(
            user=user,
            params=params,
            spreadsheet_id=spreadsheet_id
        ).get_data()

    # ===== HKD PLUS =====
    if plan_code == "hkd_plus":

        return HKDPlusSheetServiceShow(
            user=user,
            params=params,
            spreadsheet_id=spreadsheet_id
        ).get_data()

    # ===== HKD =====
    if plan_code == "hkd":

        return HKDSheetServiceShow(
            user=user,
            params=params,
            spreadsheet_id=spreadsheet_id
        ).get_data()

    # ===== FREE =====

    return FreeUserSheetServiceShow(
        user=user,
        params=params,
        spreadsheet_id=spreadsheet_id
    ).get_data()

