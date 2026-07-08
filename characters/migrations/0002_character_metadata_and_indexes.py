"""Tighten the Character schema and index the one query the API runs.

``name``, ``prompt`` and ``image`` were all nullable, so "no name" had two
representations (NULL and ""). This collapses them, records which provider
rendered each portrait, and adds the (user, -created_at) index that every read
path needs.
"""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

NULLABLE_TEXT_COLUMNS = ("name", "prompt", "image")


def collapse_nulls_to_empty(apps, schema_editor):
    """Replace NULL text with '' so the NOT NULL alterations can apply."""
    Character = apps.get_model("characters", "Character")
    for column in NULLABLE_TEXT_COLUMNS:
        Character.objects.filter(**{f"{column}__isnull": True}).update(**{column: ""})


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("characters", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(collapse_nulls_to_empty, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="character",
            name="name",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="character",
            name="prompt",
            field=models.TextField(max_length=1000),
        ),
        migrations.AlterField(
            model_name="character",
            name="image",
            field=models.ImageField(blank=True, upload_to="character_images"),
        ),
        migrations.AlterField(
            model_name="character",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="characters",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="character",
            name="provider",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="character",
            name="image_model",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="character",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="character",
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="character",
            index=models.Index(
                fields=["user", "-created_at"], name="character_owner_recent"
            ),
        ),
    ]
