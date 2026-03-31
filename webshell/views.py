import os
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages
from knowledge_base.models import LegalDocument
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import ConsultationRequestForm
from .models import WebContent
from .serializers import WebContentSerializer

from users.models import Module

def index(request):
    about_content = WebContent.objects.filter(
        content_key="about",
        is_active=True
    ).first()

    return render(request, "webshell/index.html", {
        "about_content": about_content
    })

class AppPublicBootstrapService(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # =========================
        # 1️⃣ CHỈ LẤY HKD + ENTERPRISE
        # =========================
        modules_qs = Module.objects.filter(
            is_active=True,
            code__in=["HKD", "ENTERPRISE"]
        ).order_by("sort_order")

        modules = []

        for m in modules_qs:
            modules.append({
                "code": m.code,
                "name": m.name,
                "enabled": m.is_public_enabled  # 👈 KEY CHÍNH
            })

        # =========================
        # 2️⃣ ĐẢM BẢO LUÔN ĐỦ 2 LOẠI
        # =========================
        existing_codes = {m["code"] for m in modules}

        if "HKD" not in existing_codes:
            modules.append({
                "code": "HKD",
                "name": "Hộ kinh doanh",
                "enabled": True
            })

        if "ENTERPRISE" not in existing_codes:
            modules.append({
                "code": "ENTERPRISE",
                "name": "Doanh nghiệp",
                "enabled": False
            })

        # =========================
        # 3️⃣ RESPONSE
        # =========================

        return Response({
            "account_types": modules
        })

def products(request):
    return render(request, "webshell/products.html")

def legal_center(request):
    documents = LegalDocument.objects.filter(is_active=True).order_by("-issued_date")

    return render(request, "webshell/legal_center.html", {
        "documents": documents
    })


# Dùng cho Frontend Flutter
@api_view(["GET"])
@permission_classes([AllowAny])
def legal_detail_app(request, key):

    obj = WebContent.objects.filter(
        content_key=key,
        is_active=True
    ).first()

    if not obj:
        return Response({"error": "Not found"}, status=404)

    return Response({
        "title": obj.title,
        "content": obj.content,
        "updated_at": obj.updated_at.isoformat()
    })

def guide_center(request):
    contents = WebContent.objects.filter(
        content_key__in=["faq", "about", "landing"],
        is_active=True
    )

    context = {item.content_key: item for item in contents}

    return render(request, "webshell/guide_center.html", context)

def policy(request):
    privacy = WebContent.objects.filter(
        content_key="privacy",
        is_active=True
    ).first()

    terms = WebContent.objects.filter(
        content_key="terms",
        is_active=True
    ).first()

    context = {
        "privacy": privacy,
        "terms": terms,
    }

    return render(request, "webshell/policy.html", context)

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)

            if user.is_superuser:
                return redirect("admin_portal:admin_dashboard")
            else:
                return redirect("dashboard")

        else:
            messages.error(request, "Sai email hoặc mật khẩu.")

    return render(request, "webshell/login.html")

def register_view(request):

    if request.method == "POST":
        form = ConsultationRequestForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, "webshell/register_success.html")
    else:
        form = ConsultationRequestForm()

    return render(
        request,
        "webshell/register.html",
        {"form": form}
    )

def legal_public_list(request):
    documents = LegalDocument.objects.filter(is_active=True)
    return render(request, "webshell/legal_list.html", {
        "documents": documents
    })

@api_view(["GET"])
@permission_classes([AllowAny])
def web_content_detail(request, key):

    try:
        content = WebContent.objects.get(
            content_key=key,
            is_active=True
        )
    except WebContent.DoesNotExist:
        return Response({"detail": "Not found"}, status=404)

    serializer = WebContentSerializer(content)
    return Response(serializer.data)

@api_view(["GET"])
@permission_classes([AllowAny])
def guest_slider(request):
    folder = os.path.join(settings.MEDIA_ROOT, "guest_slider")
    files = os.listdir(folder)

    data = []
    for f in files:
        data.append({
            "image_url": request.build_absolute_uri(
                f"{settings.MEDIA_URL}guest_slider/{f}"
            ),
            "title": "",
            "subtitle": "",
            "action": "report",
        })

    return Response(data)


