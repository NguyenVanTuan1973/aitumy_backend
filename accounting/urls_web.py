from django.urls import path
from . import views_web

app_name = "accounting-web"
urlpatterns = [
    # 🔐 AUTH
    path("login/", views_web.login_view, name="accounting_login"),
    path("logout/", views_web.logout_view, name="accounting_logout"),

    # 🏠 DASHBOARD
    path("", views_web.dashboard, name="accounting_dashboard"),

    # 📥 UPLOAD
    path("upload/", views_web.upload_view, name="accounting_upload"),

    path("api/upload-invoice/", views_web.api_upload_invoice, name="upload-invoice"),

    path("api/upload-invoice-in/", views_web.api_upload_invoice_in, name="upload-invoice-in"),
    path("api/upload-invoice-out/", views_web.api_upload_invoice_out, name="upload-invoice-out"),

    path("api/update-row/", views_web.api_update_row, name="update-row"),

    # Số dư đầu kỳ
    path("opening_balance/", views_web.opening_balance_view, name="opening_balance"),

    # 📄 TRANSACTION
    path("transactions/", views_web.transaction_list, name="transaction_list"),
    path("transactions/<int:id>/", views_web.transaction_detail, name="transaction_detail"),

    # 📎 DOCUMENT
    path("documents/", views_web.document_match, name="document_match"),

    # 📘 JOURNAL
    path("journals/", views_web.journal_review, name="journal_review"),

    # 📚 REGISTER
    path("registers/", views_web.register_list, name="register_list"),
    path("registers/<str:type>/", views_web.register_detail, name="register_detail"),

    path("report/so-cai/", views_web.report_so_cai, name="report_so_cai"),

    path("api/generate-journal/", views_web.api_generate_journal, name="api_generate_journal"),

    path("report/generate-s01/", views_web.api_generate_s01, name="generate_s01"),

    path("report/so-tien-gui/", views_web.report_so_tien_gui, name="report_tien_gui"),

    path("report/generate-s61/", views_web.api_generate_s61_dn_register, name="generate_s61"),

    path("report/generate-s10/", views_web.api_generate_s10_dn_register, name="generate_s10"),

    path("report/generate-s11/", views_web.api_generate_s11, name="generate_s11"),

    path("report/generate-s12/", views_web.api_generate_s12, name="generate_s12"),

    path("report/generate-s06/", views_web.api_generate_s06, name="generate_s06"),

    path("report/generate-s07/", views_web.api_generate_s07, name="generate_s07"),

    path("report/generate-s07a/", views_web.api_generate_s07a, name="generate_s07a"),

    path("report/generate-s31/", views_web.api_generate_s31, name="generate_s31"),

    path("report/generate-s34/", views_web.api_generate_s34, name="generate_s34"),

    path("report/generate-s35/", views_web.api_generate_s35, name="generate_s35"),

    path("report/generate-s36/", views_web.api_generate_s36, name="generate_s36"),

    path("report/generate-s37/", views_web.api_generate_s37, name="generate_s37"),

    path("report/generate-s38/", views_web.api_generate_s38, name="generate_s38"),

    path("report/generate-s41a/", views_web.api_generate_s41a, name="generate_s41a"),

    path("report/generate-s42a/", views_web.api_generate_s42a, name="generate_s42a"),
]