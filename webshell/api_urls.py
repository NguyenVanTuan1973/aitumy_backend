from django.urls import path
from . import views
from .views import AppPublicBootstrapService

app_name = "api/webshell"
urlpatterns = [
    path("public/bootstrap/", AppPublicBootstrapService.as_view(), name='public-bootstrap/'),
    path('products/', views.products, name='products'),
    path('legal/', views.legal_center, name='legal_center'),
    path('guides/', views.guide_center, name='guide_center'),
    path('policy/', views.policy, name='policy'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path("webcontent/<slug:key>/", views.web_content_detail, name='webcontent'),
    path('guest-slider/', views.guest_slider, name='guest-slider'),
    path("legal-detail-app/<slug:key>/", views.legal_detail_app, name='legal-detail-app'),
]
