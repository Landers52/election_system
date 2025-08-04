from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _
from django.conf.urls.static import static
from django.conf import settings
from . import views

urlpatterns = [
    # Non-i18n patterns - essential system URLs
    path('i18n/', include('django.conf.urls.i18n')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Add all routes that should support i18n
urlpatterns += i18n_patterns(
    path('', views.root_redirect, name='root_redirect'),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('voting/', include('voting.urls')),
    prefix_default_language=True,  # This will make /es/ prefix appear for Spanish
)
