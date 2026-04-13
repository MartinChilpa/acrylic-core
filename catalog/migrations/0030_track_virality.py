from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0029_track_waveform"),
    ]

    operations = [
        migrations.AddField(
            model_name="track",
            name="virality",
            field=models.FloatField(blank=True, null=True),
        ),
    ]

