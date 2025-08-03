from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('voting/', include('voting.urls')),
    path('', lambda request: redirect('voting:custom_redirect'), name='root_redirect'),
]
