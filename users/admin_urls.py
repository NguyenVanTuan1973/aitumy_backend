from django.urls import path
from . import admin_views

app_name = "users_admin"

urlpatterns = [

    # ==========================================================
    # PLAN MANAGEMENT
    # ==========================================================
    path("plans/", admin_views.plan_list, name="plan_list"),
    path("plans/create/", admin_views.plan_create, name="plan_create"),
    path("plans/<int:pk>/edit/", admin_views.plan_edit, name="plan_edit"),
    path("plans/<int:pk>/modules/", admin_views.plan_module_manage, name="plan_module_manage"),

    # ==========================================================
    # USER MANAGEMENT
    # ==========================================================
    path("users/", admin_views.user_list, name="user_list"),
    path("users/add/", admin_views.user_create, name="user_add"),
    path("users/<int:pk>/edit/", admin_views.user_update, name="user_edit"),
    path("users/<int:pk>/delete/", admin_views.user_delete, name="user_delete"),

    # ==========================================================
    # USER DRIVE
    # ==========================================================
    path("user-drives/", admin_views.user_drive_list, name="user_drive_list"),
    path("user-drives/add/", admin_views.user_drive_create, name="user_drive_add"),
    path("user-drives/<int:pk>/edit/", admin_views.user_drive_update, name="user_drive_edit"),
    path("user-drives/<int:pk>/delete/", admin_views.user_drive_delete, name="user_drive_delete"),

    # ==========================================================
    # DRIVE FOLDER
    # ==========================================================
    path("drive-folders/", admin_views.drive_folder_list, name="drive_folder_list"),
    path("drive-folders/add/", admin_views.drive_folder_create, name="drive_folder_add"),
    path("drive-folders/<int:pk>/edit/", admin_views.drive_folder_update, name="drive_folder_edit"),
    path("drive-folders/<int:pk>/delete/", admin_views.drive_folder_delete, name="drive_folder_delete"),

    # ==========================================================
    # ORGANIZATION
    # ==========================================================
    path("organizations/", admin_views.organization_list, name="organization_list"),
    path("organizations/add/", admin_views.organization_create, name="organization_add"),
    path("organizations/<int:pk>/edit/", admin_views.organization_update, name="organization_edit"),
    path("organizations/<int:pk>/delete/", admin_views.organization_delete, name="organization_delete"),

    # ==========================================================
    # INDUSTRY
    # ==========================================================
    path("industries/", admin_views.industry_list, name="industry_list"),
    path("industries/add/", admin_views.industry_create, name="industry_add"),
    path("industries/<int:pk>/edit/", admin_views.industry_update, name="industry_edit"),
    path("industries/<int:pk>/delete/", admin_views.industry_delete, name="industry_delete"),

    # ==========================================================
    # ORGANIZATION INDUSTRY
    # ==========================================================
    path("organization-industries/", admin_views.organization_industry_list, name="organization_industry_list"),
    path("organization-industries/add/", admin_views.organization_industry_create, name="organization_industry_add"),
    path("organization-industries/<int:pk>/delete/", admin_views.organization_industry_delete, name="organization_industry_delete"),
]