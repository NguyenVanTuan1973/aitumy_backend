from django.urls import path

from .views import RegisterView, LoginView, ForgotPasswordView, ChangePasswordView, CreateOrganizationAPIView, \
    BootstrapSessionAPIView, ToggleModuleAPIView, SubscriptionView, UpgradeSubscriptionView, CancelSubscriptionView, \
    OrganizationUpdateAPIView, OrganizationIndustriesUpdateAPIView, GoogleLoginAPIView
from .views.auth.activate import CompleteOnboardingAPIView

app_name = "users"
urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("auth/google-login/", GoogleLoginAPIView.as_view(), name="google-login"),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('onboarding/create-organization/', CreateOrganizationAPIView.as_view(), name='create-organization'),
    path('session/bootstrap/', BootstrapSessionAPIView.as_view(), name='bootstrap-session'),
    path('organizations/activate-module/', ToggleModuleAPIView.as_view(), name='activate-module'),
    path("auth/complete-onboarding/", CompleteOnboardingAPIView.as_view(), name='complete-onboarding'),
    path('subscription/', SubscriptionView.as_view(), name='subscription'),
    path('subscription/upgrade/', UpgradeSubscriptionView.as_view(), name='subscription-upgrade'),
    path('subscription/cancel/', CancelSubscriptionView.as_view(), name='subscription-cancel'),
    path("organizations/<int:pk>/update/",OrganizationUpdateAPIView.as_view(),name="organization-update",),
    path("organizations/<int:pk>/industries/",OrganizationIndustriesUpdateAPIView.as_view(),name="organization-industries-update",),

]