from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("club", "0002_alter_club_slug_club_unique_club_slug"),
    ]

    operations = [
        migrations.AddField(
            model_name="club",
            name="team_name",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="club",
            name="tagline",
            field=models.CharField(blank=True, default="", max_length=250),
        ),
        migrations.AddField(
            model_name="club",
            name="colors",
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AddField(
            model_name="club",
            name="auth_promo",
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AddField(
            model_name="club",
            name="sidenav",
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
    ]

