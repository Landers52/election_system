from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _
from . import views

# Non-i18n patterns (always accessible without language prefix)
urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('', views.root_redirect, name='root_redirect'),  # Root redirect without language prefix
]

# i18n patterns (accessed with language prefix)
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('voting/', include('voting.urls')),
    prefix_default_language=True,
)
