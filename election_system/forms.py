from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.models import User

from voting.models import ClientProfile


class SpanishAuthenticationForm(AuthenticationForm):
    """Authentication form that returns messages in Spanish."""

    error_messages = {
        "invalid_login": (
            "Usuario o contraseña incorrectos. Verificá los datos e intentá de nuevo. "
            "Recordá que el campo %(username)s distingue mayúsculas/minúsculas."
        ),
        "inactive": "Esta cuenta está inactiva.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        self.fields["password"].label = "Contraseña"
        self.fields["username"].widget.attrs.setdefault("placeholder", "Usuario")
        self.fields["password"].widget.attrs.setdefault("placeholder", "Contraseña")


class SpanishAdminAuthenticationForm(AdminAuthenticationForm):
    """Spanish messages for Django admin login."""

    error_messages = {
        "invalid_login": (
            "Usuario o contraseña incorrectos, o la cuenta no tiene permisos de staff para acceder al administrador. "
            "Recordá que el campo %(username)s distingue mayúsculas/minúsculas."
        ),
        "inactive": "Esta cuenta está inactiva.",
    }


class _ClientProfileFormMixin:
    organization_name = forms.CharField(
        label="Partido",
        max_length=255,
        required=False,
        help_text="Nombre interno que se mostrará en los listados administrativos.",
    )

    def _sync_organization_name(self, user: User):
        organization = (self.cleaned_data.get("organization_name") or "").strip()
        if not organization or user.is_superuser or user.username.startswith("visitor_"):
            return
        profile, _ = ClientProfile.objects.get_or_create(user=user)
        if profile.organization_name != organization:
            profile.organization_name = organization
            profile.save(update_fields=["organization_name"])


class CustomUserCreationForm(_ClientProfileFormMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization_name"].initial = "radicales"

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            self._sync_organization_name(user)
        return user


class CustomUserChangeForm(_ClientProfileFormMixin, UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = UserChangeForm.Meta.fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, "clientprofile", None)
        if profile:
            self.fields["organization_name"].initial = profile.organization_name
        else:
            self.fields["organization_name"].required = False
            self.fields["organization_name"].help_text = ""

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            self._sync_organization_name(user)
        return user
