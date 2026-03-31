# ==============================
# AUTH
# ==============================

from .auth.register import RegisterView
from .auth.login import LoginView
from .auth.password import ForgotPasswordView, ChangePasswordView
from .auth.google_login import GoogleLoginAPIView
from .auth.activate import CompleteOnboardingAPIView


# ==============================
# ORGANIZATION
# ==============================

from .organization.bootstrap import BootstrapSessionAPIView

from .organization.organization import (
    UserProfileAPIView,
    CreateOrganizationAPIView,
    OrganizationUpdateAPIView,
    OrganizationIndustriesUpdateAPIView,
    ToggleModuleAPIView,
)


# ==============================
# PERMISSIONS
# ==============================

from .permissions.module_permissions import (
    CreateMemberAPIView,
    AssignModulePermissionAPIView,
)


# ==============================
# SUBSCRIPTION
# ==============================

from .subscription.subscription import (
    SubscriptionView,
    UpgradeSubscriptionView,
    CancelSubscriptionView,
)

__all__ = [
    "RegisterView",
    "LoginView",
    "ForgotPasswordView",
    "ChangePasswordView",
    "GoogleLoginAPIView",

    "BootstrapSessionAPIView",

    "UserProfileAPIView",
    "CreateOrganizationAPIView",
    "OrganizationUpdateAPIView",
    "OrganizationIndustriesUpdateAPIView",
    "ToggleModuleAPIView",

    "CreateMemberAPIView",
    "AssignModulePermissionAPIView",

    # "PlanListAPIView",
    "SubscriptionView",
    "UpgradeSubscriptionView",
    "CancelSubscriptionView",
]