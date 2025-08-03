from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _

# Non-translated URLs
urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
]

# Translated URLs
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('voting/', include('voting.urls')),
    path('', lambda request: redirect('voting:custom_redirect'), name='root_redirect'),
    prefix_default_language=False  # This makes the default language URL not include the language prefix
)
