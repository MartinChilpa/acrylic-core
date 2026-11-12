# Historical migration restored because deployed databases already applied it.

import common.models
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("club", "0006_club_country"),
    ]

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True, default="")),
                ("slug", models.SlugField(blank=True, max_length=160)),
                ("is_active", models.BooleanField(default=True)),
                ("club", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="projects", to="club.club")),
            ],
            options={
                "ordering": ["-created"],
                "indexes": [
                    common.models.PostgresIndex(fields=["uuid"], name="club_project_uuid_idx"),
                    common.models.PostgresIndex(fields=["created"], name="club_project_created_idx"),
                    common.models.PostgresIndex(fields=["updated"], name="club_project_updated_idx"),
                    models.Index(fields=["club", "name"], name="club_projec_club_id_15ca2d_idx"),
                    models.Index(fields=["club", "slug"], name="club_projec_club_id_2383b7_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("slug", ""), _negated=True),
                        fields=("club", "slug"),
                        name="unique_project_slug_per_club",
                    ),
                ],
            },
        ),
    ]
