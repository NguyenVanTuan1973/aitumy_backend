from django.urls import path
from . import views
from .views import account_info_view, logout_view

from users.views.auth.delete_account import delete_account_view

app_name = "webshell"
urlpatterns = [
    path('', views.index, name='webshell_index'),
    path('products/', views.products, name='products'),
    path('legal/', views.legal_center, name='legal_center'),
    path('guides/', views.guide_center, name='guide_center'),
    path('faq/', views.faq_page, name='faq'),
    path('policy/', views.policy, name='policy'),
    path('login/', views.login_view, name='login'),
    path("logout/",logout_view,name="logout"),
    path('register/', views.register_view, name='register'),
    path("webcontent/<slug:key>/", views.web_content_detail, name='webcontent'),
    path('guest-slider/', views.guest_slider, name='guest-slider'),
    path('download/', views.download_app, name='download_app'),
    path("account/",account_info_view, name="account_info"),
    path("delete-account/",delete_account_view,name="delete-account"),

]
