from django.contrib import admin
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.conf import settings
from . import views
from django.http import HttpResponseRedirect

urlpatterns = [
    path('', views.root_redirect, name='root_redirect'),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('voting/', include('voting.urls')),
    re_path(r'^favicon\.ico$', lambda request: HttpResponseRedirect(settings.STATIC_URL + 'favicon.svg')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
