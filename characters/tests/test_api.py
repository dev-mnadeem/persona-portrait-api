"""HTTP contract: auth, validation, scoping, paging, failure codes."""

from __future__ import annotations

import os
from unittest import mock

from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from characters.models import Character
from characters.tests.support import FailingProvider, MediaTestCase

LIST_URL = "/api/characters/"
TOKEN_URL = "/api/auth/token/"
HEALTH_URL = "/api/health/"
PASSWORD = "portrait-pass-123"


class ApiTestCase(MediaTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("ada", PASSWORD)
        self.other = self.make_user("grace", PASSWORD)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def detail_url(self, character):
        return f"{LIST_URL}{character.pk}/"


class AuthenticationTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_listing_requires_authentication(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_creating_requires_authentication(self):
        response = self.client.post(LIST_URL, {"name": "Vale", "prompt": "a captain"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_a_token_can_be_exchanged_for_credentials(self):
        self.make_user("ada", PASSWORD)
        response = self.client.post(
            TOKEN_URL, {"username": "ada", "password": PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.json())

    def test_a_token_authenticates_subsequent_requests(self):
        self.make_user("ada", PASSWORD)
        token = self.client.post(
            TOKEN_URL, {"username": "ada", "password": PASSWORD}, format="json"
        ).json()["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(self.client.get(LIST_URL).status_code, status.HTTP_200_OK)

    def test_a_bad_password_yields_no_token(self):
        self.make_user("ada", PASSWORD)
        response = self.client.post(
            TOKEN_URL, {"username": "ada", "password": "wrong"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CreateCharacterTests(ApiTestCase):
    def test_a_valid_prompt_returns_the_stored_character(self):
        response = self.client.post(
            LIST_URL, {"name": "Vale", "prompt": "a weathered sea captain"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body["name"], "Vale")
        self.assertEqual(body["owner"], "ada")
        self.assertEqual(body["provider"], "local")
        self.assertTrue(body["image_url"].startswith("http://testserver/media/character_images/"))

    def test_the_rendered_file_lands_under_media_root(self):
        self.client.post(
            LIST_URL, {"name": "Vale", "prompt": "a weathered sea captain"}, format="json"
        )
        character = Character.objects.get()
        self.assertTrue(os.path.exists(os.path.join(settings.MEDIA_ROOT, character.image.name)))

    def test_the_character_belongs_to_the_caller(self):
        self.client.post(LIST_URL, {"name": "Vale", "prompt": "a captain"}, format="json")
        self.assertEqual(Character.objects.get().user, self.user)

    def test_a_missing_prompt_is_a_400(self):
        response = self.client.post(LIST_URL, {"name": "Vale"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("prompt", response.json())

    def test_a_missing_name_is_a_400(self):
        response = self.client.post(LIST_URL, {"prompt": "a captain"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())

    def test_a_blank_name_is_a_400(self):
        response = self.client.post(LIST_URL, {"name": "   ", "prompt": "a captain"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_an_overlong_name_is_a_400(self):
        response = self.client.post(
            LIST_URL, {"name": "V" * 101, "prompt": "a captain"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_an_overlong_prompt_is_a_400(self):
        response = self.client.post(LIST_URL, {"name": "Vale", "prompt": "a" * 1001}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_a_one_character_prompt_is_a_400(self):
        response = self.client.post(LIST_URL, {"name": "Vale", "prompt": "a"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nothing_is_stored_when_validation_fails(self):
        self.client.post(LIST_URL, {"name": "Vale"}, format="json")
        self.assertEqual(Character.objects.count(), 0)

    def test_a_provider_failure_is_a_502_not_a_500(self):
        with (
            mock.patch("characters.services.get_image_provider", return_value=FailingProvider()),
            self.assertLogs("characters.views", level="WARNING") as logged,
        ):
            response = self.client.post(
                LIST_URL, {"name": "Vale", "prompt": "a captain"}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.json()["detail"], "Image generation failed.")
        self.assertIn(FailingProvider.message, logged.output[0])

    @override_settings(IMAGE_GENERATION_RATE="1/hour")
    def test_generation_is_throttled(self):
        first = self.client.post(LIST_URL, {"name": "One", "prompt": "a captain"}, format="json")
        second = self.client.post(LIST_URL, {"name": "Two", "prompt": "a baker"}, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(IMAGE_GENERATION_RATE="1/hour")
    def test_reads_are_not_throttled_by_the_generation_budget(self):
        self.client.post(LIST_URL, {"name": "One", "prompt": "a captain"}, format="json")
        for _ in range(3):
            self.assertEqual(self.client.get(LIST_URL).status_code, status.HTTP_200_OK)


class ListCharacterTests(ApiTestCase):
    def make_character(self, name, prompt="a captain", owner=None):
        return Character.objects.create(user=owner or self.user, name=name, prompt=prompt)

    def test_only_the_callers_characters_are_listed(self):
        self.make_character("Mine")
        self.make_character("Theirs", owner=self.other)
        names = [row["name"] for row in self.client.get(LIST_URL).json()["results"]]
        self.assertEqual(names, ["Mine"])

    def test_results_are_newest_first(self):
        self.make_character("Older")
        self.make_character("Newer")
        names = [row["name"] for row in self.client.get(LIST_URL).json()["results"]]
        self.assertEqual(names, ["Newer", "Older"])

    @override_settings(CHARACTER_PAGE_SIZE=2)
    def test_the_configured_page_size_is_honoured(self):
        for index in range(5):
            self.make_character(f"Persona {index}")
        body = self.client.get(LIST_URL).json()
        self.assertEqual(body["count"], 5)
        self.assertEqual(len(body["results"]), 2)
        self.assertIsNotNone(body["next"])

    def test_page_size_can_be_set_per_request(self):
        for index in range(5):
            self.make_character(f"Persona {index}")
        body = self.client.get(LIST_URL, {"page_size": 3}).json()
        self.assertEqual(len(body["results"]), 3)

    def test_an_absurd_page_size_is_capped(self):
        self.make_character("Only one")
        body = self.client.get(LIST_URL, {"page_size": "100000"}).json()
        self.assertEqual(len(body["results"]), 1)

    def test_a_non_numeric_page_size_falls_back_to_the_default(self):
        self.make_character("Only one")
        self.assertEqual(self.client.get(LIST_URL, {"page_size": "lots"}).status_code, 200)

    def test_search_matches_the_name(self):
        self.make_character("Captain Vale")
        self.make_character("Baker Rune")
        body = self.client.get(LIST_URL, {"search": "vale"}).json()
        self.assertEqual([row["name"] for row in body["results"]], ["Captain Vale"])

    def test_search_matches_the_prompt(self):
        self.make_character("Captain Vale", prompt="a weathered sailor")
        self.make_character("Baker Rune", prompt="a cheerful baker")
        body = self.client.get(LIST_URL, {"search": "cheerful"}).json()
        self.assertEqual([row["name"] for row in body["results"]], ["Baker Rune"])

    def test_a_blank_search_is_ignored(self):
        self.make_character("Captain Vale")
        body = self.client.get(LIST_URL, {"search": "  "}).json()
        self.assertEqual(body["count"], 1)

    def test_a_character_without_an_image_reports_a_null_url(self):
        self.make_character("Captain Vale")
        self.assertIsNone(self.client.get(LIST_URL).json()["results"][0]["image_url"])

    def test_listing_cost_does_not_grow_with_the_number_of_rows(self):
        self.make_character("Only one")
        with self.assertNumQueries(2):
            self.client.get(LIST_URL)
        for index in range(10):
            self.make_character(f"Persona {index}")
        with self.assertNumQueries(2):
            self.client.get(LIST_URL)


class DetailCharacterTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.mine = Character.objects.create(user=self.user, name="Mine", prompt="a captain")
        self.theirs = Character.objects.create(user=self.other, name="Theirs", prompt="a baker")

    def test_own_character_is_readable(self):
        response = self.client.get(self.detail_url(self.mine))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], "Mine")

    def test_another_users_character_is_not_found(self):
        response = self.client.get(self.detail_url(self.theirs))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_own_character_can_be_deleted(self):
        response = self.client.delete(self.detail_url(self.mine))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Character.objects.filter(pk=self.mine.pk).exists())

    def test_another_users_character_cannot_be_deleted(self):
        response = self.client.delete(self.detail_url(self.theirs))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Character.objects.filter(pk=self.theirs.pk).exists())

    def test_deleting_removes_the_rendered_file(self):
        created = self.client.post(
            LIST_URL, {"name": "Vale", "prompt": "a captain"}, format="json"
        ).json()
        character = Character.objects.get(pk=created["id"])
        path = os.path.join(settings.MEDIA_ROOT, character.image.name)
        self.assertTrue(os.path.exists(path))

        self.client.delete(f"{LIST_URL}{character.pk}/")
        self.assertFalse(os.path.exists(path))


class HealthTests(MediaTestCase):
    def test_health_is_public_and_reports_the_provider(self):
        response = self.client.get(HEALTH_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["database"], "ok")
        self.assertEqual(body["image_provider"], "local")
        self.assertIn("openai", body["providers_available"])

    def test_health_is_reachable_by_name(self):
        self.assertEqual(reverse("health"), HEALTH_URL)
