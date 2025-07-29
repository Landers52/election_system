from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),  # Add this line before other URLs
    path('accounts/', include('django.contrib.auth.urls')),
    path('voting/', include('voting.urls')),
    path('', lambda request: redirect('voting:custom_redirect'), name='root_redirect'),
]
