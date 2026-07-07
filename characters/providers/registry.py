"""Name -> provider lookup, so adding a backend is one ``register`` call."""

from __future__ import annotations

from collections.abc import Callable

from django.conf import settings

from characters.providers.base import ImageGenerationError, ImageProvider
from characters.providers.local import LocalImageProvider
from characters.providers.openai_provider import OpenAIImageProvider

ProviderFactory = Callable[[], ImageProvider]

_FACTORIES: dict[str, ProviderFactory] = {}


def register(name: str, factory: ProviderFactory) -> None:
    """Make ``factory`` resolvable as IMAGE_PROVIDER=``name``."""
    _FACTORIES[name] = factory


def available_providers() -> list[str]:
    """Registered provider names, sorted."""
    return sorted(_FACTORIES)


def get_image_provider(name: str | None = None) -> ImageProvider:
    """Build the provider called ``name`` (default: ``settings.IMAGE_PROVIDER``).

    Raises:
        ImageGenerationError: if the name is unknown or the provider cannot be
            constructed (a missing API key, for instance).
    """
    key = (name or settings.IMAGE_PROVIDER).strip().lower()
    try:
        factory = _FACTORIES[key]
    except KeyError:
        raise ImageGenerationError(
            f"Unknown image provider {key!r}. Available: {', '.join(available_providers())}"
        ) from None
    return factory()


register("local", LocalImageProvider)
register(
    "openai",
    lambda: OpenAIImageProvider(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_IMAGE_MODEL,
        timeout=settings.OPENAI_TIMEOUT_SECONDS,
    ),
)
