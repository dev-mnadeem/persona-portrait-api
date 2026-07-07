from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from rest_framework.authtoken.views import obtain_auth_token

from ai_Influencer.views import health, media

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/token/", obtain_auth_token, name="auth-token"),
    path("api/characters/", include("characters.urls")),
    re_path(rf"^{settings.MEDIA_URL.strip('/')}/(?P<path>.+)$", media, name="media"),
]
