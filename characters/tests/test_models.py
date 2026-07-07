"""Model-level guarantees the API depends on."""

from __future__ import annotations

from characters.models import Character
from characters.tests.support import MediaTestCase


class CharacterModelTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user()

    def test_str_includes_name_and_id(self):
        character = Character.objects.create(user=self.user, name="Iris", prompt="a pilot")
        self.assertEqual(str(character), f"Iris (#{character.pk})")

    def test_default_ordering_is_newest_first(self):
        first = Character.objects.create(user=self.user, name="One", prompt="a")
        second = Character.objects.create(user=self.user, name="Two", prompt="b")
        self.assertEqual(list(Character.objects.all()), [second, first])

    def test_owner_recent_index_exists(self):
        index_names = {index.name for index in Character._meta.indexes}
        self.assertIn("character_owner_recent", index_names)

    def test_characters_are_reachable_from_the_user(self):
        Character.objects.create(user=self.user, name="Iris", prompt="a pilot")
        self.assertEqual(self.user.characters.count(), 1)

    def test_deleting_a_user_removes_their_characters(self):
        Character.objects.create(user=self.user, name="Iris", prompt="a pilot")
        self.user.delete()
        self.assertEqual(Character.objects.count(), 0)
