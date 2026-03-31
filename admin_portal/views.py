from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model, logout
from django.db.models import Count, Q
from django.utils import timezone
import PyPDF2
from support.models import Conversation, Message
from .forms import LegalUploadForm, GuideArticleForm, LandingSectionForm, WebProductForm, WebContentForm

from users.models import (
    Organization,
    OrganizationMember,
    UserSession,
    UserDrive, Module, AccountingProfile
)
from documents.models import DocumentMetadata  # nếu app documents

from knowledge_base.services.parser_service import ParserService
from knowledge_base.services.embedding_service import EmbeddingService
from knowledge_base.models import KnowledgeIndex
from knowledge_base.models import LegalDocument
from knowledge_base.services.legal_processor import process_legal_document


from support.models import Conversation

from webshell.models import WebProduct, GuideArticle, LandingSection, ConsultationRequest, WebContent

from appconfig.models import AppModule

User = get_user_model()

# ================================
# SUPERADMIN REQUIRED
# ================================
def admin_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)

# ================================
# DASHBOARD
# ================================
@admin_required
def dashboard(request):

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()

    total_orgs = Organization.objects.count()

    hkd_count = Organization.objects.filter(
        legal_form=Organization.LegalForm.HKD
    ).count()

    enterprise_count = Organization.objects.filter(
        legal_form=Organization.LegalForm.ENTERPRISE
    ).count()

    # individual_count = Organization.objects.filter(
    #     legal_form=Organization.LegalForm.INDIVIDUAL
    # ).count()

    total_modules = Module.objects.count()
    active_modules = Module.objects.filter(is_active=True).count()

    total_profiles = AccountingProfile.objects.count()

    total_drives = UserDrive.objects.count()

    total_sessions = UserSession.objects.count()

    context = {
        "total_users": total_users,
        "active_users": active_users,
        "total_orgs": total_orgs,
        "hkd_count": hkd_count,
        "enterprise_count": enterprise_count,
        "total_modules": total_modules,
        "active_modules": active_modules,
        "total_profiles": total_profiles,
        "total_drives": total_drives,
        "total_sessions": total_sessions,
    }

    # ===== LEGAL STATS =====
    total_legal_docs = LegalDocument.objects.count()

    active_legal_docs = LegalDocument.objects.filter(
        is_active=True
    ).count()

    thong_tu_count = LegalDocument.objects.filter(
        document_type="thong_tu"
    ).count()

    nghi_dinh_count = LegalDocument.objects.filter(
        document_type="nghi_dinh"
    ).count()

    chuan_muc_count = LegalDocument.objects.filter(
        document_type="chuan_muc"
    ).count()

    luat_count = LegalDocument.objects.filter(
        document_type="luat"
    ).count()

    context = {
        # existing
        "total_users": total_users,
        "active_users": active_users,
        "total_orgs": total_orgs,
        "hkd_count": hkd_count,
        "enterprise_count": enterprise_count,
        "total_modules": total_modules,
        "active_modules": active_modules,
        "total_profiles": total_profiles,
        "total_drives": total_drives,
        "total_sessions": total_sessions,

        # legal
        "total_legal_docs": total_legal_docs,
        "active_legal_docs": active_legal_docs,
        "thong_tu_count": thong_tu_count,
        "nghi_dinh_count": nghi_dinh_count,
        "chuan_muc_count": chuan_muc_count,
        "luat_count": luat_count,
    }

    return render(request, "admin_portal/dashboard.html", context)

# ================================
# USER LIST
# ================================
@admin_required
def user_list(request):
    users = (
        User.objects.annotate(
            org_count=Count("memberships", distinct=True),
            profile_count=Count(
                "memberships__organization__accounting_profiles",
                distinct=True
            )
        )
    )

    return render(request, "admin_portal/user_list.html", {
        "users": users
    })

@admin_required
def organization_list(request):
    orgs = Organization.objects.annotate(
        member_count=Count("members"),
        profile_count=Count("accounting_profiles")
    ).order_by("-created_at")

    return render(request, "admin_portal/org_list.html", {
        "orgs": orgs
    })

@admin_required
def module_list(request):
    modules = Module.objects.annotate(
        org_count=Count("organization_modules")
    )

    return render(request, "admin_portal/module_list.html", {
        "modules": modules
    })

@admin_required
def profile_list(request):
    profiles = AccountingProfile.objects.select_related(
        "organization",
        "module",
        "accounting_regime",
        "owner"
    )

    return render(request, "admin_portal/profile_list.html", {
        "profiles": profiles
    })

# ================================
# USER DETAIL
# ================================
@admin_required
def user_detail(request, user_id):

    user = get_object_or_404(
        User.objects.prefetch_related(
            "memberships__organization",
            "modules__module",
        ).select_related(
            "drive"
        ),
        id=user_id
    )

    modules = user.modules.select_related("module")

    drive = getattr(user, "drive", None)

    sessions = UserSession.objects.filter(
        user=user
    ).select_related(
        "organization",
        "active_module"
    ).order_by("-created_at")[:20]

    memberships = user.memberships.select_related("organization")

    return render(request, "admin_portal/user_detail.html", {
        "user_obj": user,
        "modules": modules,
        "drive": drive,
        "sessions": sessions,
        "memberships": memberships,
    })

# ================================
# TOGGLE USER STATUS
# ================================
@admin_required
def toggle_user_status(request, user_id):

    user = get_object_or_404(User, id=user_id)

    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])

    # 🚀 Nếu disable thì revoke toàn bộ session
    if not user.is_active:
        UserSession.objects.filter(
            user=user,
            is_active=True
        ).update(is_active=False)

    return redirect("admin_portal:admin_user_detail", user_id=user.id)

# ================================
# DRIVE STATUS
# ================================
@admin_required
def drive_status(request):
    drives = UserDrive.objects.select_related("user")

    return render(request, "admin_portal/drive_status.html", {
        "drives": drives
    })

# ================================
# SYSTEM LOGS
# ================================
@admin_required
def logs_view(request):

    sessions = UserSession.objects.select_related(
        "user",
        "organization",
        "active_module"
    ).order_by("-created_at")[:100]

    return render(request, "admin_portal/logs.html", {
        "sessions": sessions
    })

@admin_required
def toggle_member_status(request, member_id):
    member = get_object_or_404(OrganizationMember, id=member_id)
    member.is_active = not member.is_active
    member.save(update_fields=["is_active"])

    return redirect("admin_portal:admin_user_detail",
                    user_id=member.user.id)


@admin_required
def revoke_session(request, session_id):
    session = get_object_or_404(UserSession, id=session_id)

    session.is_active = False
    session.save(update_fields=["is_active"])

    return redirect(
        "admin_portal:admin_user_detail",
        user_id=session.user.id
    )

# ================================
# LOGOUT
# ================================
def admin_logout(request):
    logout(request)
    return redirect("webshell:login")

# ==============================
# LIST VIEW
# ==============================

@admin_required
def legal_list(request):
    documents = LegalDocument.objects.order_by("-created_at")
    return render(request, "admin_portal/legal_list.html", {
        "documents": documents
    })

# ==============================
# DETAIL VIEW
# ==============================
@admin_required
def legal_detail(request, pk):
    document = get_object_or_404(LegalDocument, pk=pk)
    return render(request, "admin_portal/legal_detail.html", {
        "document": document
    })

# ==============================
# UPLOAD VIEW
# ==============================

@admin_required
def legal_upload(request):
    form = LegalUploadForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        document = form.save()

        process_legal_document(document)

        messages.success(request, "Upload thành công. Đang xử lý...")
        return redirect("admin_portal:admin_legal_list")

    return render(request, "admin_portal/legal_upload.html", {
        "form": form
    })

# ==============================
# INDEX FUNCTION
# ==============================
def index_legal_document(document: LegalDocument):

    parser = ParserService()
    embedder = EmbeddingService()

    # 1️⃣ Đọc file PDF
    pdf_reader = PyPDF2.PdfReader(document.file.path)

    full_text = ""
    for page in pdf_reader.pages:
        full_text += page.extract_text() or ""

    clean_text = parser.clean_text(full_text)

    # 2️⃣ Chunk
    chunks = parser.chunk_text(clean_text, chunk_size=500)

    # 3️⃣ Embed từng chunk
    for chunk in chunks:
        embedding = embedder.embed_text(chunk)
        keywords = parser.extract_keywords(chunk)

        KnowledgeIndex.objects.create(
            content_type="legal_document",
            object_id=document.id,
            text_content=chunk,
            embedding=embedding,
            keywords=keywords
        )

# ==============================
# SUPPORT - INBOX
# ==============================
@admin_required
def admin_support_conversations(request):
    conversations = Conversation.objects.all().order_by("-updated_at")
    return render(
        request,
        "admin_portal/support_list.html",
        {"conversations": conversations}
    )

@admin_required
def admin_support_detail(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    messages = conversation.messages.all().order_by("created_at")

    return render(
        request,
        "admin_portal/support_detail.html",
        {
            "conversation": conversation,
            "messages": messages
        }
    )

@admin_required
def admin_reply_conversation(request, pk):
    if request.method != "POST":
        return redirect("admin_portal:admin_support_detail", pk=pk)

    conversation = get_object_or_404(Conversation, pk=pk)

    # ✅ sửa ở đây
    if conversation.status == "closed":
        messages.error(request, "Conversation is already closed.")
        return redirect("admin_portal:admin_support_detail", pk=pk)

    content = request.POST.get("message", "").strip()

    if not content:
        messages.error(request, "Message cannot be empty.")
        return redirect("admin_portal:admin_support_detail", pk=pk)

    # ✅ sửa sender → sender_type
    Message.objects.create(
        conversation=conversation,
        sender_type="admin",
        content=content,
    )

    # 🔥 cập nhật thời gian
    conversation.last_message_at = timezone.now()
    conversation.last_admin_reply_at = timezone.now()
    conversation.save(update_fields=[
        "last_message_at",
        "last_admin_reply_at",
        "updated_at",
    ])

    messages.success(request, "Reply sent successfully.")
    return redirect("admin_portal:admin_support_detail", pk=pk)

@admin_required
def admin_close_conversation(request, pk):
    if request.method != "POST":
        return redirect("admin_portal:admin_support_detail", pk=pk)

    conversation = get_object_or_404(Conversation, pk=pk)

    if conversation.status == "closed":
        messages.warning(request, "Conversation is already closed.")
        return redirect("admin_portal:admin_support_detail", pk=pk)

    # ✅ sửa chỗ này
    conversation.status = "closed"
    conversation.save(update_fields=["status"])

    messages.success(request, "Conversation closed successfully.")
    return redirect("admin_portal:admin_support_detail", pk=pk)

# ==============================
# WEBSHELL - PRODUCT
# ==============================
@admin_required
def admin_product_list(request):
    products = WebProduct.objects.all().order_by("id")
    return render(request, "admin_portal/products/list.html", {
        "products": products
    })

@admin_required
def admin_product_create(request):
    if request.method == "POST":
        form = WebProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("admin_portal:admin_product_list")
    else:
        form = WebProductForm()

    return render(request, "admin_portal/products/form.html", {
        "form": form
    })

@admin_required
def admin_product_edit(request, pk):
    product = get_object_or_404(WebProduct, pk=pk)

    if request.method == "POST":
        form = WebProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect("admin_portal:admin_product_list")
    else:
        form = WebProductForm(instance=product)

    return render(request, "admin_portal/products/form.html", {
        "form": form
    })

# ==============================
# WEBSHELL - GuideArticle
# ==============================
@admin_required
def admin_guide_list(request):
    guides = GuideArticle.objects.all().order_by("-created_at")
    return render(request, "admin_portal/guides/list.html", {
        "guides": guides
    })

@admin_required
def admin_guide_create(request):
    if request.method == "POST":
        form = GuideArticleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("admin_portal:admin_guide_list")
    else:
        form = GuideArticleForm()

    return render(request, "admin_portal/guides/form.html", {
        "form": form
    })

@admin_required
def admin_guide_edit(request, pk):
    guide = get_object_or_404(GuideArticle, pk=pk)

    if request.method == "POST":
        form = GuideArticleForm(request.POST, instance=guide)
        if form.is_valid():
            form.save()
            return redirect("admin_portal:admin_guide_list")
    else:
        form = GuideArticleForm(instance=guide)

    return render(request, "admin_portal/guides/form.html", {
        "form": form
    })

# ==============================
# WEBSHELL - LandingSection
# ==============================
@admin_required
def admin_landing_section_list(request):
    sections = LandingSection.objects.all().order_by("order")

    return render(request, "admin_portal/landing/list.html", {
        "landing_list": sections
    })

@admin_required
def admin_landing_section_create(request):
    if request.method == "POST":
        form = LandingSectionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("admin_portal:admin_landing_section_list")
    else:
        form = LandingSectionForm()

    return render(request, "admin_portal/landing/form.html", {
        "form": form
    })

@admin_required
def admin_landing_section_edit(request, pk):
    section = get_object_or_404(LandingSection, pk=pk)

    if request.method == "POST":
        form = LandingSectionForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            return redirect("admin_portal:admin_landing_section_list")
    else:
        form = LandingSectionForm(instance=section)

    return render(request, "admin_portal/landing/form.html", {
        "form": form
    })

# ==============================
# WEBSHELL - WebContent (Policy / FAQ / About / Pricing...)
# ==============================

@admin_required
def admin_webcontent_list(request):
    contents = WebContent.objects.all().order_by("content_key")

    return render(
        request,
        "admin_portal/webcontent/list.html",
        {"contents": contents},
    )

@admin_required
def admin_webcontent_create(request):
    if request.method == "POST":
        form = WebContentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("admin_portal:admin_webcontent_list")
    else:
        form = WebContentForm()

    return render(
        request,
        "admin_portal/webcontent/form.html",
        {"form": form},
    )

@admin_required
def admin_webcontent_edit(request, pk):
    content = get_object_or_404(WebContent, pk=pk)

    if request.method == "POST":
        form = WebContentForm(request.POST, instance=content)
        if form.is_valid():
            form.save()
            return redirect("admin_portal:admin_webcontent_list")
    else:
        form = WebContentForm(instance=content)

    return render(
        request,
        "admin_portal/webcontent/form.html",
        {"form": form},
    )

# ==============================
# WEBSHELL - Consultation Register
# ==============================
@admin_required
def consultation_list(request):
    consultations = ConsultationRequest.objects.all().order_by("-created_at")

    return render(
        request,
        "admin_portal/consultation_list.html",
        {"consultations": consultations},
    )

@admin_required
def consultation_detail(request, pk):
    consultation = get_object_or_404(ConsultationRequest, pk=pk)

    return render(
        request,
        "admin_portal/consultation_detail.html",
        {"consultation": consultation},
    )

@admin_required
def toggle_consultation_status(request, pk):
    consultation = get_object_or_404(ConsultationRequest, pk=pk)
    consultation.is_contacted = not consultation.is_contacted
    consultation.save()
    return redirect("admin_portal:admin_consultation_list")

