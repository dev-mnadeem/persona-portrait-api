from django.contrib.auth.models import User
from django.db import models

NAME_MAX_LENGTH = 100
PROMPT_MAX_LENGTH = 1000
PROVIDER_MAX_LENGTH = 32
MODEL_MAX_LENGTH = 64


class Character(models.Model):
    """A persona and the portrait generated for it."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="characters")
    name = models.CharField(max_length=NAME_MAX_LENGTH)
    prompt = models.TextField(max_length=PROMPT_MAX_LENGTH)
    image = models.ImageField(upload_to="character_images", blank=True)
    provider = models.CharField(max_length=PROVIDER_MAX_LENGTH, blank=True)
    image_model = models.CharField(max_length=MODEL_MAX_LENGTH, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            # Every read path is "this user's characters, newest first".
            models.Index(fields=["user", "-created_at"], name="character_owner_recent"),
        ]

    def __str__(self) -> str:
        return f"{self.name} (#{self.pk})"
