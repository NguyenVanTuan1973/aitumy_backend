from django.urls import path
from . import views_admin

app_name = "accounting"

urlpatterns = [

    path("regulations/", views_admin.regulation_list, name="regulation_list"),
    path("regulations/create/", views_admin.regulation_create, name="regulation_create"),

    path("accounts/", views_admin.account_list, name="account_list"),
    path("accounts/create/", views_admin.account_create, name="account_create"),
    path("accounts/<int:pk>/edit/", views_admin.account_edit, name="account_edit"),
]