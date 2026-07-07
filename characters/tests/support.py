"""Shared fixtures: a temp MEDIA_ROOT and providers that fail on demand."""

from __future__ import annotations

import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings

from characters.providers import GeneratedImage, ImageGenerationError, ImageProvider

# A one-pixel PNG is enough for anything that only needs "some valid bytes".
ONE_PIXEL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d4944415478da63fcffff3f0300050001ff9b3ba800"
    "00000049454e44ae426082"
)

#: High enough that only the throttling test itself ever trips it.
UNTHROTTLED_RATE = "1000/hour"


class StubProvider(ImageProvider):
    """Returns fixed bytes and records the calls it received."""

    name = "stub"

    def __init__(self, data: bytes = ONE_PIXEL_PNG, content_type: str = "image/png") -> None:
        self.data = data
        self.content_type = content_type
        self.calls: list[tuple[str, str]] = []

    def generate(self, prompt: str, *, size: str) -> GeneratedImage:
        self.calls.append((prompt, size))
        return GeneratedImage(
            data=self.data,
            provider=self.name,
            model="stub-v1",
            content_type=self.content_type,
        )


class FailingProvider(ImageProvider):
    """Always raises, to exercise the error path end to end."""

    name = "failing"
    message = "upstream refused the prompt"

    def generate(self, prompt: str, *, size: str) -> GeneratedImage:
        raise ImageGenerationError(self.message)


class MediaTestCase(TestCase):
    """Base case with an isolated MEDIA_ROOT and predictable throttles."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._media_root = tempfile.mkdtemp(prefix="persona-media-")
        cls._settings = override_settings(
            MEDIA_ROOT=cls._media_root,
            IMAGE_PROVIDER="local",
            IMAGE_SIZE="64x64",
            CHARACTER_PAGE_SIZE=20,
            IMAGE_GENERATION_RATE=UNTHROTTLED_RATE,
        )
        cls._settings.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        cls._settings.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)

    def setUp(self) -> None:
        super().setUp()
        cache.clear()

    @staticmethod
    def make_user(username: str = "ada", password: str = "portrait-pass-123") -> User:
        return User.objects.create_user(username=username, password=password)
