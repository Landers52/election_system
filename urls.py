from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from election_system.forms import SpanishAuthenticationForm
from voting.views import redirect_to_dashboard  # Import the new view
from voting import views as voting_views  # Import views from the voting app
from . import views


urlpatterns = [
    path("", redirect_to_dashboard, name="home"),  # Add this line for the root path
    path("voting/", include("voting.urls")),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(authentication_form=SpanishAuthenticationForm),
        name="login",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path('logout/', views.logout_view, name='logout'),
    path('voting/import/', voting_views.import_voters, name='import_voters'),  # Ensure this points to the voting app
    path('i18n/', include('django.conf.urls.i18n')),
]