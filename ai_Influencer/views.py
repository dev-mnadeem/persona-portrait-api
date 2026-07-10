"""Project-level endpoints that belong to no single app."""

from __future__ import annotations

from django.conf import settings
from django.db import connection
from django.http import HttpRequest, JsonResponse

from characters.providers import available_providers

HTTP_SERVICE_UNAVAILABLE = 503


def health(request: HttpRequest) -> JsonResponse:  # noqa: ARG001 - Django view signature
    """Liveness plus a database round-trip, for probes and compose healthchecks."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # noqa: BLE001 - any DB failure is the same signal here
        database_ok = False
    else:
        database_ok = True

    payload = {
        "status": "ok" if database_ok else "degraded",
        "database": "ok" if database_ok else "unavailable",
        "image_provider": settings.IMAGE_PROVIDER,
        "providers_available": available_providers(),
    }
    return JsonResponse(payload, status=200 if database_ok else HTTP_SERVICE_UNAVAILABLE)
