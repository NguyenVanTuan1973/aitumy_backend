from django.urls import path
from .views import RegisterGenerateView

urlpatterns = [
    path("register/generate/", RegisterGenerateView.as_view(), name="generate_register"),
]