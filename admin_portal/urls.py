from django.urls import include, path
from . import views


app_name = "admin_portal"
urlpatterns = [
    path("", views.dashboard, name="admin_dashboard"),

    path("drive-status/", views.drive_status, name="admin_drive_status"),
    path("logs/", views.logs_view, name="admin_logs"),
    path("logout/", views.admin_logout, name="logout"),
    path("members/<int:member_id>/toggle/", views.toggle_member_status, name="admin_toggle_member"),

    path("sessions/<int:session_id>/revoke/", views.revoke_session, name="admin_revoke_session"),

    path("legal/", views.legal_list, name="admin_legal_list"),
    path("legal/upload/", views.legal_upload, name="admin_legal_upload"),
    path("legal/<int:pk>/", views.legal_detail, name="admin_legal_detail"),

    path("support/", views.admin_support_conversations, name="admin_support_conversations"),
    path("support/<int:pk>/", views.admin_support_detail, name="admin_support_detail"),
    path("support/<int:pk>/reply/", views.admin_reply_conversation, name="admin_reply_conversation"),
    path("support/<int:pk>/close/", views.admin_close_conversation, name="admin_close_conversation"),

    path("products/", views.admin_product_list, name="admin_product_list"),
    path("products/create/", views.admin_product_create, name="admin_product_create"),
    path("products/<int:pk>/edit/", views.admin_product_edit, name="admin_product_edit"),

    path("guides/", views.admin_guide_list, name="admin_guide_list"),
    path("guides/create/", views.admin_guide_create, name="admin_guide_create"),
    path("guides/<int:pk>/edit/", views.admin_guide_edit, name="admin_guide_edit"),

    path("landing/", views.admin_landing_section_list, name="admin_landing_section_list"),
    path("landing/create/", views.admin_landing_section_create, name="admin_landing_section_create"),
    path("landing/<int:pk>/edit/", views.admin_landing_section_edit, name="admin_landing_section_edit"),

    path("consultations/", views.consultation_list, name="admin_consultation_list"),
    path("consultations/<int:pk>/", views.consultation_detail, name="admin_consultation_detail"),
    path("consultations/<int:pk>/toggle/", views.toggle_consultation_status, name="admin_toggle_consultation"),

    path("webcontent/", views.admin_webcontent_list, name="admin_webcontent_list"),
    path("webcontent/create/", views.admin_webcontent_create, name="admin_webcontent_create"),
    path("webcontent/<int:pk>/edit/", views.admin_webcontent_edit, name="admin_webcontent_edit"),

]
