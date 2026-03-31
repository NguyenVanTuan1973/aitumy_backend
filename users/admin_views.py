from django.contrib.auth.hashers import make_password
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Plan, Module, PlanModule, Organization, Industry, OrganizationIndustry, User, UserDrive, DriveFolder


def user_list(request):
    users = User.objects.all().order_by("-date_joined")
    return render(request, "users/admin/user_list.html", {
        "users": users
    })

def user_create(request):
    if request.method == "POST":
        email = request.POST.get("email")
        full_name = request.POST.get("full_name")
        password = request.POST.get("password")
        is_superuser = bool(request.POST.get("is_superuser"))
        is_active = bool(request.POST.get("is_active"))

        user = User.objects.create(
            email=email,
            full_name=full_name,
            is_superuser=is_superuser,
            is_staff=is_superuser,
            is_active=is_active,
            password=make_password(password)
        )

        messages.success(request, "Tạo người dùng thành công!")
        return redirect("users_admin:user_list")

    return render(request, "users/admin/user_form.html")

def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        user.email = request.POST.get("email")
        user.full_name = request.POST.get("full_name")
        user.is_superuser = bool(request.POST.get("is_superuser"))
        user.is_staff = user.is_superuser
        user.is_active = bool(request.POST.get("is_active"))
        user.save()

        messages.success(request, "Cập nhật người dùng thành công!")
        return redirect("users_admin:user_list")

    return render(request, "users/admin/user_form.html", {
        "user_obj": user
    })

def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)

    if user.is_superuser:
        messages.error(request, "Không thể xóa Superuser!")
        return redirect("users_admin:user_list")

    user.delete()
    messages.success(request, "Xóa người dùng thành công!")
    return redirect("users_admin:user_list")

def plan_list(request):
    plans = Plan.objects.all()
    return render(request, "users/admin/plan_list.html", {"plans": plans})

def plan_create(request):
    if request.method == "POST":
        name = request.POST.get("name")
        code = request.POST.get("code")
        price = request.POST.get("price")
        is_active = request.POST.get("is_active") == "on"

        if not name or not code:
            messages.error(request, "Vui lòng nhập đầy đủ thông tin")
            return redirect("users_admin:plan_create")

        Plan.objects.create(
            name=name,
            code=code,
            price=price or 0,
            is_active=is_active,
        )

        messages.success(request, "Tạo gói thành công")
        return redirect("users_admin:plan_list")

    return render(request, "users/admin/plan_form.html", {
        "is_edit": False
    })

def plan_edit(request, pk):
    plan = get_object_or_404(Plan, pk=pk)

    if request.method == "POST":
        plan.name = request.POST.get("name")
        plan.code = request.POST.get("code")
        plan.price = request.POST.get("price") or 0
        plan.is_active = request.POST.get("is_active") == "on"
        plan.save()

        messages.success(request, "Cập nhật gói thành công")
        return redirect("users_admin:plan_list")

    return render(request, "users/admin/plan_form.html", {
        "plan": plan,
        "is_edit": True
    })

def module_list(request):
    modules = Module.objects.all()
    return render(request, "users/admin/module_list.html", {"modules": modules})

def plan_module_manage(request, pk):
    plan = get_object_or_404(Plan, pk=pk)

    modules = Module.objects.filter(is_active=True)

    if request.method == "POST":
        selected_modules = request.POST.getlist("modules")

        # Xóa hết cũ
        PlanModule.objects.filter(plan=plan).delete()

        # Thêm lại
        for module_id in selected_modules:
            PlanModule.objects.create(
                plan=plan,
                module_id=module_id
            )

        messages.success(request, "Cập nhật module cho gói thành công")
        return redirect("users_admin:plan_list")

    assigned_ids = PlanModule.objects.filter(plan=plan).values_list("module_id", flat=True)

    return render(request, "users/admin/plan_module_manage.html", {
        "plan": plan,
        "modules": modules,
        "assigned_ids": assigned_ids
    })

def user_drive_list(request):
    drives = UserDrive.objects.select_related("user")
    return render(request, "users/admin/user_drive_list.html", {
        "drives": drives
    })

def user_drive_create(request):
    users = User.objects.all()

    if request.method == "POST":
        UserDrive.objects.create(
            user_id=request.POST.get("user"),
            total_storage=request.POST.get("total_storage") or 0,
            used_storage=request.POST.get("used_storage") or 0,
        )
        messages.success(request, "Tạo Drive thành công!")
        return redirect("users_admin:user_drive_list")

    return render(request, "users/admin/user_drive_form.html", {
        "users": users
    })

def user_drive_update(request, pk):
    drive = get_object_or_404(UserDrive, pk=pk)
    users = User.objects.all()

    if request.method == "POST":
        drive.user_id = request.POST.get("user")
        drive.total_storage = request.POST.get("total_storage") or 0
        drive.used_storage = request.POST.get("used_storage") or 0
        drive.save()

        messages.success(request, "Cập nhật Drive thành công!")
        return redirect("users_admin:user_drive_list")

    return render(request, "users/admin/user_drive_form.html", {
        "drive": drive,
        "users": users
    })

def user_drive_delete(request, pk):
    drive = get_object_or_404(UserDrive, pk=pk)
    drive.delete()

    messages.success(request, "Xóa Drive thành công!")
    return redirect("users_admin:user_drive_list")

def drive_folder_list(request):
    folders = DriveFolder.objects.select_related(
        "drive__user",
        "parent_folder"
    ).order_by("-created_at")

    return render(request, "users/admin/drive_folder_list.html", {
        "folders": folders
    })

def drive_folder_create(request):
    users = User.objects.all()
    folders = DriveFolder.objects.all()

    if request.method == "POST":
        DriveFolder.objects.create(
            user_id=request.POST.get("user"),
            name=request.POST.get("name"),
            parent_id=request.POST.get("parent") or None,
        )
        messages.success(request, "Tạo thư mục thành công!")
        return redirect("users_admin:drive_folder_list")

    return render(request, "users/admin/drive_folder_form.html", {
        "users": users,
        "folders": folders
    })

def drive_folder_update(request, pk):
    folder = get_object_or_404(DriveFolder, pk=pk)
    users = User.objects.all()
    folders = DriveFolder.objects.exclude(pk=pk)

    if request.method == "POST":
        folder.user_id = request.POST.get("user")
        folder.name = request.POST.get("name")
        folder.parent_id = request.POST.get("parent") or None
        folder.save()

        messages.success(request, "Cập nhật thư mục thành công!")
        return redirect("users_admin:drive_folder_list")

    return render(request, "users/admin/drive_folder_form.html", {
        "folder": folder,
        "users": users,
        "folders": folders
    })

def drive_folder_delete(request, pk):
    folder = get_object_or_404(DriveFolder, pk=pk)
    folder.delete()

    messages.success(request, "Xóa thư mục thành công!")
    return redirect("users_admin:drive_folder_list")

# ==========================================================
# ORGANIZATION
# ==========================================================
def organization_list(request):
    organizations = Organization.objects.all().order_by("-created_at")
    return render(request, "users/admin/organization_list.html", {
        "organizations": organizations
    })

def organization_create(request):
    if request.method == "POST":
        name = request.POST.get("name")
        address = request.POST.get("address")
        tax_code = request.POST.get("tax_code")
        legal_form = request.POST.get("legal_form")

        Organization.objects.create(
            name=name,
            address=address,
            tax_code=tax_code,
            legal_form=legal_form
        )
        messages.success(request, "Thêm tổ chức thành công!")
        return redirect("users_admin:organization_list")

    return render(request, "users/admin/organization_form.html")

def organization_update(request, pk):
    org = get_object_or_404(Organization, pk=pk)

    if request.method == "POST":
        org.name = request.POST.get("name")
        org.address = request.POST.get("address")
        org.tax_code = request.POST.get("tax_code")
        org.legal_form = request.POST.get("legal_form")
        org.save()

        messages.success(request, "Cập nhật tổ chức thành công!")
        return redirect("users_admin:organization_list")

    return render(request, "users/admin/organization_form.html", {
        "organization": org
    })

def organization_delete(request, pk):
    org = get_object_or_404(Organization, pk=pk)
    org.delete()
    messages.success(request, "Xóa tổ chức thành công!")
    return redirect("users_admin:organization_list")

# ==========================================================
# INDUSTRY
# ==========================================================
def industry_list(request):
    industries = Industry.objects.all()
    return render(request, "users/admin/industry_list.html", {
        "industries": industries
    })

def industry_create(request):
    if request.method == "POST":
        Industry.objects.create(
            code=request.POST.get("code"),
            name=request.POST.get("name"),
            vat_percent=request.POST.get("vat_percent") or 0,
            pit_percent=request.POST.get("pit_percent") or 0,
            is_active=True if request.POST.get("is_active") else False,
        )

        messages.success(request, "Thêm ngành nghề thành công!")
        return redirect("users_admin:industry_list")

    return render(request, "users/admin/industry_form.html")

def industry_update(request, pk):
    industry = get_object_or_404(Industry, pk=pk)

    if request.method == "POST":
        industry.name = request.POST.get("name")
        industry.code = request.POST.get("code")
        industry.save()

        messages.success(request, "Cập nhật ngành nghề thành công!")
        return redirect("users_admin:industry_list")

    return render(request, "users/admin/industry_form.html", {
        "industry": industry
    })

def industry_delete(request, pk):
    industry = get_object_or_404(Industry, pk=pk)
    industry.delete()
    messages.success(request, "Xóa ngành nghề thành công!")
    return redirect("users_admin:industry_list")

# ==========================================================
# ORGANIZATION INDUSTRY
# ==========================================================
def organization_industry_list(request):
    items = OrganizationIndustry.objects.select_related("organization", "industry")
    return render(request, "users/admin/organization_industry_list.html", {
        "items": items
    })

def organization_industry_create(request):
    organizations = Organization.objects.all()
    industries = Industry.objects.all()

    if request.method == "POST":
        OrganizationIndustry.objects.create(
            organization_id=request.POST.get("organization"),
            industry_id=request.POST.get("industry")
        )
        messages.success(request, "Gán ngành nghề thành công!")
        return redirect("users_admin:organization_industry_list")

    return render(request, "users/admin/organization_industry_form.html", {
        "organizations": organizations,
        "industries": industries
    })

def organization_industry_delete(request, pk):
    item = get_object_or_404(OrganizationIndustry, pk=pk)
    item.delete()
    messages.success(request, "Xóa liên kết thành công!")
    return redirect("users_admin:organization_industry_list")