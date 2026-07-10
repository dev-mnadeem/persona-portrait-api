"""The provider seam: determinism offline, correct mapping online."""

from __future__ import annotations

import base64
import io
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings
from PIL import Image

from characters.providers import (
    GeneratedImage,
    ImageGenerationError,
    LocalImageProvider,
    OpenAIImageProvider,
    available_providers,
    get_image_provider,
    register,
)
from characters.providers.registry import _FACTORIES


class GeneratedImageTests(SimpleTestCase):
    def test_extension_follows_content_type(self):
        for content_type, expected in [
            ("image/png", "png"),
            ("image/jpeg", "jpg"),
            ("image/webp", "webp"),
        ]:
            with self.subTest(content_type=content_type):
                image = GeneratedImage(b"", "p", "m", content_type)
                self.assertEqual(image.extension, expected)

    def test_unknown_content_type_falls_back_to_png(self):
        image = GeneratedImage(b"", "p", "m", "application/octet-stream")
        self.assertEqual(image.extension, "png")


class LocalImageProviderTests(SimpleTestCase):
    def setUp(self):
        self.provider = LocalImageProvider()

    def test_same_prompt_produces_identical_bytes(self):
        first = self.provider.generate("a tired detective", size="64x64")
        second = self.provider.generate("a tired detective", size="64x64")
        self.assertEqual(first.data, second.data)

    def test_different_prompts_produce_different_bytes(self):
        first = self.provider.generate("a tired detective", size="64x64")
        second = self.provider.generate("a cheerful baker", size="64x64")
        self.assertNotEqual(first.data, second.data)

    def test_output_is_a_png_of_the_requested_size(self):
        result = self.provider.generate("a tired detective", size="128x96")
        with Image.open(io.BytesIO(result.data)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (128, 96))

    def test_provenance_is_recorded(self):
        result = self.provider.generate("anything", size="64x64")
        self.assertEqual(result.provider, "local")
        self.assertEqual(result.model, "local-identicon-v1")
        self.assertEqual(result.content_type, "image/png")

    def test_unparseable_size_is_rejected(self):
        with self.assertRaises(ImageGenerationError):
            self.provider.generate("x", size="huge")

    def test_oversized_request_is_rejected(self):
        with self.assertRaises(ImageGenerationError):
            self.provider.generate("x", size="9999x9999")

    def test_undersized_request_is_rejected(self):
        with self.assertRaises(ImageGenerationError):
            self.provider.generate("x", size="4x4")


class RegistryTests(SimpleTestCase):
    def test_local_resolves_to_the_local_provider(self):
        self.assertIsInstance(get_image_provider("local"), LocalImageProvider)

    def test_name_is_case_and_space_insensitive(self):
        self.assertIsInstance(get_image_provider("  LOCAL "), LocalImageProvider)

    @override_settings(IMAGE_PROVIDER="local")
    def test_default_comes_from_settings(self):
        self.assertIsInstance(get_image_provider(), LocalImageProvider)

    def test_unknown_provider_lists_the_alternatives(self):
        with self.assertRaises(ImageGenerationError) as caught:
            get_image_provider("midjourney")
        self.assertIn("local", str(caught.exception))

    def test_both_builtin_providers_are_registered(self):
        self.assertEqual(available_providers(), ["local", "openai"])

    @override_settings(OPENAI_API_KEY="")
    def test_openai_without_a_key_is_a_clear_error(self):
        with self.assertRaises(ImageGenerationError) as caught:
            get_image_provider("openai")
        self.assertIn("OPENAI_API_KEY", str(caught.exception))

    def test_a_new_backend_needs_one_register_call(self):
        class Noop(LocalImageProvider):
            name = "noop"

        register("noop", Noop)
        try:
            self.assertIsInstance(get_image_provider("noop"), Noop)
            self.assertIn("noop", available_providers())
        finally:
            _FACTORIES.pop("noop")


def _fake_response(payload):
    return SimpleNamespace(data=payload)


class OpenAIImageProviderTests(SimpleTestCase):
    """Exercised against a stub client: no network, no key spent."""

    def _provider(self, client):
        provider = OpenAIImageProvider(api_key="sk-test", model="gpt-image-1", timeout=1)
        provider._client = client
        return provider

    def test_empty_api_key_is_refused_at_construction(self):
        with self.assertRaises(ImageGenerationError):
            OpenAIImageProvider(api_key="", model="gpt-image-1", timeout=1)

    def test_base64_payload_is_decoded(self):
        encoded = base64.b64encode(b"portrait-bytes").decode()
        client = SimpleNamespace(
            images=SimpleNamespace(
                generate=lambda **kwargs: _fake_response([SimpleNamespace(b64_json=encoded)])
            )
        )
        result = self._provider(client).generate("a knight", size="1024x1024")
        self.assertEqual(result.data, b"portrait-bytes")
        self.assertEqual(result.provider, "openai")
        self.assertEqual(result.model, "gpt-image-1")

    def test_prompt_and_size_are_forwarded(self):
        seen = {}

        def capture(**kwargs):
            seen.update(kwargs)
            encoded = base64.b64encode(b"x").decode()
            return _fake_response([SimpleNamespace(b64_json=encoded)])

        client = SimpleNamespace(images=SimpleNamespace(generate=capture))
        self._provider(client).generate("a knight", size="512x512")
        self.assertEqual(seen["prompt"], "a knight")
        self.assertEqual(seen["size"], "512x512")
        self.assertEqual(seen["n"], 1)

    def test_empty_data_is_an_error(self):
        client = SimpleNamespace(
            images=SimpleNamespace(generate=lambda **kwargs: _fake_response([]))
        )
        with self.assertRaises(ImageGenerationError):
            self._provider(client).generate("a knight", size="512x512")

    def test_missing_b64_field_is_an_error(self):
        client = SimpleNamespace(
            images=SimpleNamespace(
                generate=lambda **kwargs: _fake_response([SimpleNamespace(b64_json=None)])
            )
        )
        with self.assertRaises(ImageGenerationError):
            self._provider(client).generate("a knight", size="512x512")

    def test_undecodable_payload_is_an_error(self):
        client = SimpleNamespace(
            images=SimpleNamespace(
                generate=lambda **kwargs: _fake_response([SimpleNamespace(b64_json="!!!!")])
            )
        )
        with self.assertRaises(ImageGenerationError):
            self._provider(client).generate("a knight", size="512x512")

    def test_transport_failure_is_wrapped(self):
        def explode(**kwargs):
            raise TimeoutError("connection reset")

        client = SimpleNamespace(images=SimpleNamespace(generate=explode))
        with self.assertRaises(ImageGenerationError) as caught:
            self._provider(client).generate("a knight", size="512x512")
        self.assertIn("connection reset", str(caught.exception))
