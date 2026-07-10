"""Pagination that honours the live setting rather than an import-time copy."""

from __future__ import annotations

from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request

MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1


class CharacterPagination(PageNumberPagination):
    """Page size comes from ``CHARACTER_PAGE_SIZE``, overridable per request.

    DRF's own ``PAGE_SIZE`` is read into a class attribute when the module is
    imported, which makes it invisible to environment changes and to
    ``override_settings``. Reading it per request keeps one source of truth.
    """

    page_size_query_param = "page_size"
    max_page_size = MAX_PAGE_SIZE

    def get_page_size(self, request: Request) -> int:
        requested = request.query_params.get(self.page_size_query_param)
        if requested:
            try:
                return min(max(int(requested), MIN_PAGE_SIZE), self.max_page_size)
            except ValueError:
                pass
        return settings.CHARACTER_PAGE_SIZE
