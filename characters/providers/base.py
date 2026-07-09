"""The seam between "describe a persona" and "get pixels back"."""

from __future__ import annotations

import abc
from dataclasses import dataclass

CONTENT_TYPE_EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}
DEFAULT_EXTENSION = "png"


class ImageGenerationError(RuntimeError):
    """A provider could not produce an image.

    Raised for misconfiguration, transport failures and unusable responses
    alike. The view layer turns this into a single 502 so that callers never
    see a provider-specific exception type.
    """


@dataclass(frozen=True)
class GeneratedImage:
    """One rendered portrait plus the provenance needed to store it."""

    data: bytes
    provider: str
    model: str
    content_type: str = "image/png"

    @property
    def extension(self) -> str:
        """File extension matching ``content_type`` ('png' for anything odd)."""
        return CONTENT_TYPE_EXTENSIONS.get(self.content_type, DEFAULT_EXTENSION)


class ImageProvider(abc.ABC):
    """Anything that can turn a prompt into image bytes.

    Implementations must be safe to construct without network access; do the
    credential check in ``__init__`` and the network call in ``generate``.
    """

    #: Registry key, e.g. "openai".
    name: str = ""

    @abc.abstractmethod
    def generate(self, prompt: str, *, size: str) -> GeneratedImage:
        """Render ``prompt`` at ``size`` ("WIDTHxHEIGHT").

        Raises:
            ImageGenerationError: if no image could be produced.
        """
