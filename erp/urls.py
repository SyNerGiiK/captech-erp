from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static

from portal import views as portal_views

def health(_):
    return HttpResponse("ok", content_type="text/plain")

urlpatterns = [
    path("admin/healthz/", health, name="healthz"),

    # ↓↓↓ notre route spécifique AVANT l'admin Django
    path("admin/dashboard/", portal_views.admin_dashboard, name="admin_dashboard"),

    path("admin/", admin.site.urls),
    path("", include("portal.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)