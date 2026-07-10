"""CharacterStudio: generate, store, record provenance."""

from __future__ import annotations

import os

from django.conf import settings
from django.test import SimpleTestCase

from characters.models import Character
from characters.providers import ImageGenerationError, LocalImageProvider
from characters.services import CharacterStudio, build_filename
from characters.tests.support import FailingProvider, MediaTestCase, StubProvider


class BuildFilenameTests(SimpleTestCase):
    def test_name_is_slugified_into_the_filename(self):
        self.assertTrue(build_filename("Captain Vale", "png").startswith("captain-vale-"))

    def test_extension_is_applied(self):
        self.assertTrue(build_filename("Captain Vale", "webp").endswith(".webp"))

    def test_unsluggable_names_fall_back(self):
        self.assertTrue(build_filename("???", "png").startswith("character-"))

    def test_repeated_calls_do_not_collide(self):
        names = {build_filename("Captain Vale", "png") for _ in range(20)}
        self.assertEqual(len(names), 20)


class CharacterStudioTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user()

    def test_created_character_is_persisted_with_a_file(self):
        studio = CharacterStudio(StubProvider())
        character = studio.create_character(user=self.user, name="Vale", prompt="a captain")

        self.assertEqual(Character.objects.count(), 1)
        self.assertTrue(character.image.name.startswith("character_images/"))
        self.assertTrue(os.path.exists(os.path.join(settings.MEDIA_ROOT, character.image.name)))

    def test_provenance_comes_from_the_provider(self):
        character = CharacterStudio(StubProvider()).create_character(
            user=self.user, name="Vale", prompt="a captain"
        )
        self.assertEqual(character.provider, "stub")
        self.assertEqual(character.image_model, "stub-v1")

    def test_prompt_and_configured_size_reach_the_provider(self):
        provider = StubProvider()
        CharacterStudio(provider).create_character(user=self.user, name="Vale", prompt="a captain")
        self.assertEqual(provider.calls, [("a captain", "64x64")])

    def test_size_can_be_overridden_per_studio(self):
        provider = StubProvider()
        CharacterStudio(provider, size="32x32").create_character(
            user=self.user, name="Vale", prompt="a captain"
        )
        self.assertEqual(provider.calls[0][1], "32x32")

    def test_content_type_decides_the_stored_extension(self):
        provider = StubProvider(content_type="image/webp")
        character = CharacterStudio(provider).create_character(
            user=self.user, name="Vale", prompt="a captain"
        )
        self.assertTrue(character.image.name.endswith(".webp"))

    def test_a_provider_failure_writes_nothing(self):
        studio = CharacterStudio(FailingProvider())
        with self.assertRaises(ImageGenerationError):
            studio.create_character(user=self.user, name="Vale", prompt="a captain")
        self.assertEqual(Character.objects.count(), 0)

    def test_provider_is_resolved_from_settings_when_not_injected(self):
        self.assertIsInstance(CharacterStudio().provider, LocalImageProvider)

    def test_no_provider_is_constructed_until_first_use(self):
        studio = CharacterStudio()
        self.assertIsNone(studio._provider)
