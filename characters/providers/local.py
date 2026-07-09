"""Offline provider: deterministic abstract portraits, no network, no key.

This is what makes the repo runnable and testable without credentials. The
same prompt always produces byte-identical PNG output, so tests can assert on
it directly.
"""

from __future__ import annotations

import hashlib
import io

from PIL import Image, ImageDraw

from characters.providers.base import GeneratedImage, ImageGenerationError, ImageProvider

#: Portraits are drawn on a coarse grid and scaled up, which keeps output small
#: and makes two prompts visibly different at a glance.
GRID = 8
MAX_DIMENSION = 2048
MIN_DIMENSION = 32
BACKDROP_BYTES = slice(0, 3)
PALETTE_SIZE = 3


def _parse_size(size: str) -> tuple[int, int]:
    """Parse a "WIDTHxHEIGHT" string into a validated (width, height) pair."""
    try:
        width_text, height_text = size.lower().split("x", 1)
        width, height = int(width_text), int(height_text)
    except ValueError as exc:
        raise ImageGenerationError(f"Unparseable image size: {size!r}") from exc
    if not (MIN_DIMENSION <= width <= MAX_DIMENSION and MIN_DIMENSION <= height <= MAX_DIMENSION):
        raise ImageGenerationError(
            f"Image size {size!r} is outside {MIN_DIMENSION}-{MAX_DIMENSION} pixels"
        )
    return width, height


class LocalImageProvider(ImageProvider):
    """Derive a symmetric colour field from the SHA-256 of the prompt."""

    name = "local"
    model = "local-identicon-v1"

    def generate(self, prompt: str, *, size: str) -> GeneratedImage:
        width, height = _parse_size(size)
        digest = hashlib.sha256(prompt.encode("utf-8")).digest()

        backdrop = tuple(digest[BACKDROP_BYTES])
        palette = [
            tuple(digest[offset : offset + 3]) for offset in range(3, 3 + PALETTE_SIZE * 3, 3)
        ]

        canvas = Image.new("RGB", (GRID, GRID), backdrop)
        painter = ImageDraw.Draw(canvas)
        for row in range(GRID):
            for column in range(GRID // 2):
                bit = digest[(row * GRID + column) % len(digest)]
                if bit % 2:
                    continue
                colour = palette[bit % PALETTE_SIZE]
                painter.point((column, row), fill=colour)
                painter.point((GRID - 1 - column, row), fill=colour)

        canvas = canvas.resize((width, height), Image.NEAREST)
        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG", optimize=True)
        return GeneratedImage(
            data=buffer.getvalue(),
            provider=self.name,
            model=self.model,
            content_type="image/png",
        )
