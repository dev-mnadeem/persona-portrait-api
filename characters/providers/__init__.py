"""Image generation backends behind one interface."""

from characters.providers.base import (
    GeneratedImage,
    ImageGenerationError,
    ImageProvider,
)
from characters.providers.local import LocalImageProvider
from characters.providers.openai_provider import OpenAIImageProvider
from characters.providers.registry import (
    available_providers,
    get_image_provider,
    register,
)

__all__ = [
    "GeneratedImage",
    "ImageGenerationError",
    "ImageProvider",
    "LocalImageProvider",
    "OpenAIImageProvider",
    "available_providers",
    "get_image_provider",
    "register",
]
