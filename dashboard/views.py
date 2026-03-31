from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def overview(request):
    return render(request, "dashboard/overview.html")


@login_required
def transactions(request):
    return render(request, "dashboard/transactions.html")


@login_required
def ai(request):
    return render(request, "dashboard/ai.html")


@login_required
def support(request):
    return render(request, "dashboard/support.html")


@login_required
def profile(request):
    return render(request, "dashboard/profile.html")
