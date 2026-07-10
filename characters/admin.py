from django.contrib import admin
from django.utils.html import format_html

from characters.models import Character

THUMBNAIL_PIXELS = 80


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "provider", "image_model", "created_at")
    list_filter = ("provider", "image_model", "created_at")
    list_select_related = ("user",)
    search_fields = ("name", "prompt", "user__username")
    readonly_fields = ("created_at", "preview")
    ordering = ("-created_at",)

    @admin.display(description="Preview")
    def preview(self, character: Character) -> str:
        """Render the stored portrait inline on the change form."""
        if not character.image:
            return "—"
        return format_html(
            '<img src="{}" style="max-width:{}px;height:auto;" alt="{}">',
            character.image.url,
            THUMBNAIL_PIXELS,
            character.name,
        )
