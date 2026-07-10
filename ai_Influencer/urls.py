from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token

from ai_Influencer.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/token/", obtain_auth_token, name="auth-token"),
    path("api/characters/", include("characters.urls")),
]

if settings.DEBUG:
    # In production the portraits under MEDIA_ROOT are served by the front door
    # (nginx, S3, a CDN) rather than by Django.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
