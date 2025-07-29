from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from voting.views import redirect_to_dashboard  # Import the new view
from voting import views as voting_views  # Import views from the voting app
from . import views


urlpatterns = [
    path("", redirect_to_dashboard, name="home"),  # Add this line for the root path
    path("voting/", include("voting.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path('logout/', views.logout_view, name='logout'),
    path('voting/import/', voting_views.import_voters, name='import_voters'),  # Ensure this points to the voting app
    path('i18n/', include('django.conf.urls.i18n')),
]