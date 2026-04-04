from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("artist", "0021_fix_empty_spotify_popularity"),
    ]

    operations = [
        migrations.AddField(
            model_name="artist",
            name="chartmetric_instagram_sports_fit_percent",
            field=models.FloatField(default=0, editable=False),
        ),
    ]
