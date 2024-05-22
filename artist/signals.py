from django.db.models.signals import post_save
from django.dispatch import receiver
from artist.models import Artist
from artist.tasks import create_artist_in_hubspot_task


@receiver(post_save, sender=Artist)
def artist_created(sender, instance, created, **kwargs):
    # when an artist is created / create it in hubspot
    if created:
        create_artist_in_hubspot_task.delay(instance.id)
