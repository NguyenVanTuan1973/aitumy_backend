from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Organization)
admin.site.register(OrganizationMember)
admin.site.register(Plan)
admin.site.register(UserDrive)
admin.site.register(DriveFolder)
admin.site.register(Subscription)
admin.site.register(SubscriptionPeriod)
admin.site.register(Payment)
admin.site.register(Module)
admin.site.register(PlanModule)
admin.site.register(OrganizationModule)
admin.site.register(AccountingProfile)
admin.site.register(ProfileUser)
admin.site.register(ProfileDrive)
admin.site.register(UserSession)
admin.site.register(Industry)
admin.site.register(OrganizationIndustry)

