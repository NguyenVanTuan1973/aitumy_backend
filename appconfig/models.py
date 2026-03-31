from django.db import models
from users.models import Module


class AppSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()

    description = models.CharField(max_length=255, blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.key

# AppModule (nhóm hệ thống)
class AppModule(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class SidebarMenu(models.Model):

    code = models.CharField(max_length=50, unique=True)

    title = models.CharField(max_length=255)
    icon = models.CharField(max_length=100)

    app_module = models.ForeignKey(
        AppModule,
        on_delete=models.CASCADE,
        related_name="menus"
    )

    action = models.CharField(max_length=50)

    feature_module = models.ForeignKey(
        Module,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children"
    )

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class MediaAsset(models.Model):
    name = models.CharField(max_length=255)

    file = models.ImageField(upload_to="assets/")

    asset_type = models.CharField(
        max_length=50,
        choices=(
            ("logo", "Logo"),
            ("banner", "Banner"),
            ("icon", "Icon"),
        )
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name