from django.urls import path
from . import admin_views

app_name = "appconfig_admin"

urlpatterns = [

    # AppSetting
    path("settings/", admin_views.setting_list, name="setting_list"),
    path("settings/create/", admin_views.setting_create, name="setting_create"),
    path("settings/<int:pk>/edit/", admin_views.setting_edit, name="setting_edit"),
    path("settings/<int:pk>/delete/", admin_views.setting_delete, name="setting_delete"),

    # AppModule
    path("modules/", admin_views.module_list, name="module_list"),
    path("modules/create/", admin_views.module_create, name="module_create"),
    path("modules/<int:pk>/edit/", admin_views.module_edit, name="module_edit"),
    path("modules/<int:pk>/delete/", admin_views.module_delete, name="module_delete"),

    # SidebarMenu
    path("sidebar/", admin_views.sidebar_list, name="sidebar_list"),
    path("sidebar/create/", admin_views.sidebar_create, name="sidebar_create"),
    path("sidebar/<int:pk>/edit/", admin_views.sidebar_edit, name="sidebar_edit"),
    path("sidebar/<int:pk>/delete/", admin_views.sidebar_delete, name="sidebar_delete"),

    # MediaAsset
    path("media/", admin_views.media_list, name="media_list"),
    path("media/create/", admin_views.media_create, name="media_create"),
    path("media/<int:pk>/delete/", admin_views.media_delete, name="media_delete"),
]