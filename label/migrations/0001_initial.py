from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Label",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                ("label_name", models.CharField(max_length=150, verbose_name="Nombre del Label")),
                ("portal_web", models.URLField(blank=True, max_length=255, verbose_name="Sitio Web")),
                ("slug", models.SlugField(blank=True, max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "user",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="label",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Label",
                "verbose_name_plural": "Labels",
            },
        ),
        migrations.AddConstraint(
            model_name="label",
            constraint=models.UniqueConstraint(
                condition=models.Q(("slug", ""), _negated=True),
                fields=("slug",),
                name="unique_label_slug",
            ),
        ),
    ]

