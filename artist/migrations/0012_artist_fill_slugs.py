from django.db import migrations
from django.utils.text import slugify


def fill_slug(apps, schema_editor):
    Artist = apps.get_model('artist', 'Artist')
    for artist in Artist.objects.all():
        artist.slug = slugify(artist.name)
        artist.save()


class Migration(migrations.Migration):

    dependencies = [
        ('artist', '0011_artist_slug'),
    ]

    operations = [
        migrations.RunPython(fill_slug),
    ]