"""OpenAI-backed provider.

The ``openai`` package is imported lazily so the rest of the project — tests
included — runs whether or not it is installed.
"""

from __future__ import annotations

import base64
import binascii

from characters.providers.base import GeneratedImage, ImageGenerationError, ImageProvider


class OpenAIImageProvider(ImageProvider):
    """Call the OpenAI images endpoint and return raw PNG bytes."""

    name = "openai"

    def __init__(self, *, api_key: str, model: str, timeout: float) -> None:
        if not api_key:
            raise ImageGenerationError(
                "OPENAI_API_KEY is empty. Set it, or set IMAGE_PROVIDER=local."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on install extras
            raise ImageGenerationError(
                "The 'openai' package is not installed. "
                "Run `pip install -r requirements.txt`, or set IMAGE_PROVIDER=local."
            ) from exc

        self.model = model
        self._client = OpenAI(api_key=api_key, timeout=timeout)

    def generate(self, prompt: str, *, size: str) -> GeneratedImage:
        try:
            response = self._client.images.generate(
                model=self.model,
                prompt=prompt,
                size=size,
                n=1,
            )
        except Exception as exc:  # noqa: BLE001 - provider errors are opaque by design
            raise ImageGenerationError(f"OpenAI image request failed: {exc}") from exc

        payload = getattr(response, "data", None)
        if not payload:
            raise ImageGenerationError("OpenAI returned no image data")

        encoded = getattr(payload[0], "b64_json", None)
        if not encoded:
            raise ImageGenerationError("OpenAI returned an image without inline base64 data")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ImageGenerationError("OpenAI returned undecodable image data") from exc

        return GeneratedImage(
            data=data,
            provider=self.name,
            model=self.model,
            content_type="image/png",
        )
