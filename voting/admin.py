from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import ClientProfile, Voter

# Inline for ClientProfile
class ClientProfileInline(admin.StackedInline):
    model = ClientProfile
    fk_name = "user"
    verbose_name_plural = "Client Profile"

# Custom UserAdmin to include ClientProfile
class CustomUserAdmin(UserAdmin):
    inlines = (ClientProfileInline,)

# Register models
admin.site.register(Voter)

# Update User admin with custom admin class
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
