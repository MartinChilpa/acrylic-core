from django.db import migrations, models
import django.db.models.deletion


def copy_favorite_track_to_project_track(apps, schema_editor):
    ProjectTrack = apps.get_model("club", "ProjectTrack")
    for project_track in ProjectTrack.objects.select_related("favorite").iterator():
        project_track.track_id = project_track.favorite.track_id
        project_track.save(update_fields=["track"])


def restore_favorite_from_track(apps, schema_editor):
    ProjectTrack = apps.get_model("club", "ProjectTrack")
    TrackFavorite = apps.get_model("club", "TrackFavorite")
    for project_track in ProjectTrack.objects.select_related("project").iterator():
        favorite, _ = TrackFavorite.objects.get_or_create(
            club_id=project_track.project.club_id,
            track_id=project_track.track_id,
        )
        project_track.favorite_id = favorite.id
        project_track.save(update_fields=["favorite"])


class Migration(migrations.Migration):

    dependencies = [
        ("club", "0010_project_projecttrack"),
    ]

    operations = [
        migrations.AddField(
            model_name="projecttrack",
            name="track",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="project_tracks",
                to="catalog.track",
            ),
        ),
        migrations.RunPython(copy_favorite_track_to_project_track, restore_favorite_from_track),
        migrations.RemoveConstraint(
            model_name="projecttrack",
            name="unique_project_track",
        ),
        migrations.RemoveIndex(
            model_name="projecttrack",
            name="club_projec_project_874108_idx",
        ),
        migrations.RemoveField(
            model_name="projecttrack",
            name="favorite",
        ),
        migrations.AlterField(
            model_name="projecttrack",
            name="track",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="project_tracks",
                to="catalog.track",
            ),
        ),
        migrations.AddConstraint(
            model_name="projecttrack",
            constraint=models.UniqueConstraint(fields=("project", "track"), name="unique_project_track"),
        ),
        migrations.AddIndex(
            model_name="projecttrack",
            index=models.Index(fields=["project", "track"], name="club_projec_project_8a692e_idx"),
        ),
    ]
