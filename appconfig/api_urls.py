from django.urls import path
from .api import SidebarMenuListAPIView

urlpatterns = [
    path("sidebar-menus/", SidebarMenuListAPIView.as_view(), name="sidebar-menu-list"),
]