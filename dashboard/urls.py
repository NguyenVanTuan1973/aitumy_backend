from django.urls import path
from . import views

urlpatterns = [
    path('', views.overview, name='dashboard_overview'),
    path('transactions/', views.transactions, name='dashboard_transactions'),
    path('ai/', views.ai, name='dashboard_ai'),
    path('support/', views.support, name='dashboard_support'),
    path('profile/', views.profile, name='dashboard_profile'),
]
