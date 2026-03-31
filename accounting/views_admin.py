from django.shortcuts import render, get_object_or_404, redirect
from .models import Regulation, Account
from .forms import RegulationForm, AccountForm


# ======================
# REGULATION
# ======================

def regulation_list(request):
    regulations = Regulation.objects.all()
    return render(request, "accounting/regulation_list.html", {
        "regulations": regulations
    })


def regulation_create(request):
    form = RegulationForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("accounting:regulation_list")

    return render(request, "accounting/regulation_form.html", {
        "form": form
    })


# ======================
# ACCOUNT
# ======================

def account_list(request):
    accounts = Account.objects.select_related("parent", "regulation").all()
    return render(request, "accounting/account_list.html", {
        "accounts": accounts
    })


def account_create(request):
    form = AccountForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("accounting:account_list")

    return render(request, "accounting/account_form.html", {
        "form": form
    })


def account_edit(request, pk):
    account = get_object_or_404(Account, pk=pk)
    form = AccountForm(request.POST or None, instance=account)

    if form.is_valid():
        form.save()
        return redirect("accounting:account_list")

    return render(request, "accounting/account_form.html", {
        "form": form
    })