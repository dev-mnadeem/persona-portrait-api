"""Business logic: prompt in, stored Character out.

The view layer never talks to a provider or to the filesystem directly.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify

from characters.models import Character
from characters.providers import ImageProvider, get_image_provider

FILENAME_SLUG_LENGTH = 40
FILENAME_UNIQUE_LENGTH = 12
FALLBACK_SLUG = "character"


def build_filename(name: str, extension: str) -> str:
    """A collision-proof, filesystem-safe name that still reads like the persona."""
    stem = slugify(name)[:FILENAME_SLUG_LENGTH] or FALLBACK_SLUG
    return f"{stem}-{uuid.uuid4().hex[:FILENAME_UNIQUE_LENGTH]}.{extension}"


class CharacterStudio:
    """Generates portraits and persists them.

    The provider is injected, so tests (and any future async worker) can swap
    in a stub without touching settings.
    """

    def __init__(self, provider: ImageProvider | None = None, *, size: str | None = None) -> None:
        self._provider = provider
        self._size = size or settings.IMAGE_SIZE

    @property
    def provider(self) -> ImageProvider:
        """Resolve the configured provider on first use, not at import time."""
        if self._provider is None:
            self._provider = get_image_provider()
        return self._provider

    def create_character(self, *, user: User, name: str, prompt: str) -> Character:
        """Render ``prompt``, store the image, and return the saved row.

        Raises:
            ImageGenerationError: if the provider could not produce an image.
                Nothing is written to the database in that case.
        """
        image = self.provider.generate(prompt, size=self._size)

        with transaction.atomic():
            character = Character(
                user=user,
                name=name,
                prompt=prompt,
                provider=image.provider,
                image_model=image.model,
            )
            character.image.save(
                build_filename(name, image.extension),
                ContentFile(image.data),
                save=False,
            )
            character.save()
        return character
