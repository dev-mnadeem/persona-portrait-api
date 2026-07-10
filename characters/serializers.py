"""Request validation and response shaping."""

from __future__ import annotations

from rest_framework import serializers

from characters.models import NAME_MAX_LENGTH, PROMPT_MAX_LENGTH, Character

MIN_PROMPT_LENGTH = 3


class CharacterSerializer(serializers.ModelSerializer):
    """Read shape: what a client gets back for a stored character."""

    owner = serializers.CharField(source="user.username", read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Character
        fields = [
            "id",
            "name",
            "prompt",
            "image_url",
            "provider",
            "image_model",
            "owner",
            "created_at",
        ]
        read_only_fields = fields

    def get_image_url(self, character: Character) -> str | None:
        """Absolute URL of the stored portrait, or null if none was saved."""
        if not character.image:
            return None
        url = character.image.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request is not None else url


class CharacterCreateSerializer(serializers.Serializer):
    """Write shape: the two fields the caller actually supplies."""

    name = serializers.CharField(max_length=NAME_MAX_LENGTH, trim_whitespace=True)
    prompt = serializers.CharField(
        max_length=PROMPT_MAX_LENGTH,
        min_length=MIN_PROMPT_LENGTH,
        trim_whitespace=True,
    )
