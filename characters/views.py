"""Thin HTTP layer: validate, delegate to the service, serialize."""

from __future__ import annotations

import logging

from django.conf import settings
from django.db.models import Q, QuerySet
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from characters.models import Character
from characters.providers import ImageGenerationError
from characters.serializers import CharacterCreateSerializer, CharacterSerializer
from characters.services import CharacterStudio

logger = logging.getLogger(__name__)

SEARCH_PARAM = "search"


class ImageGenerationThrottle(UserRateThrottle):
    """Separate budget for the one endpoint that spends money per call."""

    scope = "image-generation"

    def get_rate(self) -> str:
        # Read the live setting instead of DRF's import-time THROTTLE_RATES copy.
        return settings.IMAGE_GENERATION_RATE


class OwnedCharactersMixin:
    """Restrict every queryset to the requesting user's own characters."""

    serializer_class = CharacterSerializer

    def get_queryset(self) -> QuerySet[Character]:
        # select_related('user') keeps the serializer's `owner` field from
        # issuing one extra query per row.
        return Character.objects.filter(user=self.request.user).select_related("user")


class CharacterListCreateView(OwnedCharactersMixin, generics.ListCreateAPIView):
    """``GET`` the caller's characters, ``POST`` to generate a new one."""

    def get_throttles(self):
        if self.request.method == "POST":
            return [ImageGenerationThrottle()]
        return super().get_throttles()

    def get_queryset(self) -> QuerySet[Character]:
        queryset = super().get_queryset()
        search = self.request.query_params.get(SEARCH_PARAM, "").strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(prompt__icontains=search))
        return queryset

    def create(self, request: Request, *args, **kwargs) -> Response:
        form = CharacterCreateSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        try:
            character = CharacterStudio().create_character(
                user=request.user,
                name=form.validated_data["name"],
                prompt=form.validated_data["prompt"],
            )
        except ImageGenerationError as exc:
            logger.warning("Image generation failed for user %s: %s", request.user.pk, exc)
            return Response(
                {"detail": "Image generation failed.", "reason": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        body = CharacterSerializer(character, context=self.get_serializer_context()).data
        return Response(body, status=status.HTTP_201_CREATED)


class CharacterDetailView(OwnedCharactersMixin, generics.RetrieveDestroyAPIView):
    """Fetch or delete one of the caller's characters."""

    def perform_destroy(self, instance: Character) -> None:
        # Drop the rendered file too, so deletes do not leak disk.
        instance.image.delete(save=False)
        instance.delete()
