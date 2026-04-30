from django.db import migrations
from django.utils.text import slugify


def fill_missing_slugs(apps, schema_editor):
    Club = apps.get_model("club", "Club")

    clubs = Club.objects.filter(slug="").only("id", "club_name", "slug")
    for club in clubs.iterator():
        base = slugify(club.club_name or "") or "club"
        slug = base
        suffix = 2
        while Club.objects.filter(slug=slug).exclude(id=club.id).exists():
            slug = f"{base}-{suffix}"
            suffix += 1
        club.slug = slug
        club.save(update_fields=["slug"])


class Migration(migrations.Migration):
    dependencies = [
        ("club", "0003_club_team_config_fields"),
    ]

    operations = [
        migrations.RunPython(fill_missing_slugs, migrations.RunPython.noop),
    ]

