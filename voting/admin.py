from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from election_system.forms import SpanishAdminAuthenticationForm
from .models import ClientProfile, Voter


class ClientProfileInline(admin.StackedInline):
    model = ClientProfile
    fk_name = "user"
    can_delete = False
    extra = 0
    fields = ("organization_name", "visitor_username_display")
    readonly_fields = ("visitor_username_display",)
    verbose_name_plural = "Perfil del cliente"

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "organization_name" and formfield is not None:
            formfield.label = "Partido"
        return formfield

    def visitor_username_display(self, obj):
        if obj and obj.visitor_user:
            return obj.visitor_user.username
        return "—"

    visitor_username_display.short_description = "Usuario visitante"

    # Do not show inline on the add user page; profile is created by signal
    def has_add_permission(self, request, obj=None):
        return obj is not None


class CustomUserAdmin(UserAdmin):
    inlines = (ClientProfileInline,)

    def get_inline_instances(self, request, obj=None):
        # Hide inlines on add form to avoid duplicate OneToOne creation
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)


admin.site.register(Voter)
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Use Spanish messages on the Django admin login form
admin.site.login_form = SpanishAdminAuthenticationForm
