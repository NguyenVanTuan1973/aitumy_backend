from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import AppSetting, AppModule, SidebarMenu, MediaAsset


# ================== APP SETTING ==================

def setting_list(request):
    items = AppSetting.objects.all()
    return render(request, "appconfig/admin/setting_list.html", {"items": items})


def setting_create(request):
    if request.method == "POST":
        AppSetting.objects.create(
            key=request.POST.get("key"),
            value=request.POST.get("value"),
        )
        messages.success(request, "Tạo cấu hình thành công")
        return redirect("appconfig_admin:setting_list")

    return render(request, "appconfig/admin/setting_form.html")


def setting_edit(request, pk):
    item = get_object_or_404(AppSetting, pk=pk)

    if request.method == "POST":
        item.key = request.POST.get("key")
        item.value = request.POST.get("value")
        item.save()
        messages.success(request, "Cập nhật thành công")
        return redirect("appconfig_admin:setting_list")

    return render(request, "appconfig/admin/setting_form.html", {"item": item})


def setting_delete(request, pk):
    item = get_object_or_404(AppSetting, pk=pk)
    item.delete()
    messages.success(request, "Đã xóa cấu hình")
    return redirect("appconfig_admin:setting_list")


# ================== APP MODULE ==================

def module_list(request):
    modules = AppModule.objects.all()
    return render(request, "appconfig/admin/module_list.html", {"modules": modules})


def module_create(request):
    if request.method == "POST":
        AppModule.objects.create(
            code=request.POST.get("code"),
            name=request.POST.get("name"),
            is_active=bool(request.POST.get("is_active"))
        )
        messages.success(request, "Tạo module thành công")
        return redirect("appconfig_admin:module_list")

    return render(request, "appconfig/admin/module_form.html")


def module_edit(request, pk):
    module = get_object_or_404(AppModule, pk=pk)

    if request.method == "POST":
        module.code = request.POST.get("code")
        module.name = request.POST.get("name")
        module.is_active = bool(request.POST.get("is_active"))
        module.save()
        messages.success(request, "Cập nhật thành công")
        return redirect("appconfig_admin:module_list")

    return render(request, "appconfig/admin/module_form.html", {"module": module})


def module_delete(request, pk):
    module = get_object_or_404(AppModule, pk=pk)
    module.delete()
    messages.success(request, "Đã xóa module")
    return redirect("appconfig_admin:module_list")


# ================== SIDEBAR ==================

def sidebar_list(request):
    menus = SidebarMenu.objects.select_related("app_module")
    return render(request, "appconfig/admin/sidebar_list.html", {"menus": menus})


def sidebar_create(request):
    modules = AppModule.objects.all()

    if request.method == "POST":
        SidebarMenu.objects.create(
            app_module_id=request.POST.get("app_module"),
            title=request.POST.get("title"),
            code=request.POST.get("code"),
            icon=request.POST.get("icon"),
            action=request.POST.get("action"),
            module_code=request.POST.get("module_code"),
            order=request.POST.get("order") or 0,
            is_active=bool(request.POST.get("is_active"))
        )
        messages.success(request, "Tạo menu thành công")
        return redirect("appconfig_admin:sidebar_list")

    return render(request, "appconfig/admin/sidebar_form.html", {"modules": modules})


def sidebar_edit(request, pk):
    menu = get_object_or_404(SidebarMenu, pk=pk)
    modules = AppModule.objects.all()

    if request.method == "POST":
        menu.app_module_id = request.POST.get("app_module")
        menu.title = request.POST.get("title")
        menu.code = request.POST.get("code")
        menu.icon = request.POST.get("icon")
        menu.action = request.POST.get("action")
        menu.module_code = request.POST.get("module_code")
        menu.order = request.POST.get("order") or 0
        menu.is_active = bool(request.POST.get("is_active"))
        menu.save()
        messages.success(request, "Cập nhật thành công")
        return redirect("appconfig_admin:sidebar_list")

    return render(request, "appconfig/admin/sidebar_form.html", {
        "menu": menu,
        "modules": modules
    })


def sidebar_delete(request, pk):
    menu = get_object_or_404(SidebarMenu, pk=pk)
    menu.delete()
    messages.success(request, "Đã xóa menu")
    return redirect("appconfig_admin:sidebar_list")


# ================== MEDIA ==================

def media_list(request):
    items = MediaAsset.objects.all()
    return render(request, "appconfig/admin/media_list.html", {"items": items})


def media_create(request):
    if request.method == "POST":
        MediaAsset.objects.create(
            name=request.POST.get("name"),
            file=request.FILES.get("file"),
        )
        messages.success(request, "Upload thành công")
        return redirect("appconfig_admin:media_list")

    return render(request, "appconfig/admin/media_form.html")


def media_delete(request, pk):
    item = get_object_or_404(MediaAsset, pk=pk)
    item.delete()
    messages.success(request, "Đã xóa file")
    return redirect("appconfig_admin:media_list")