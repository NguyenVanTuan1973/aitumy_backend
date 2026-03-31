from django.contrib import admin
from .models import AppSetting, AppModule, SidebarMenu, MediaAsset

admin.site.register(AppSetting)
admin.site.register(AppModule)
admin.site.register(SidebarMenu)
admin.site.register(MediaAsset)