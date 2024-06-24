from django.db.models.signals import post_save
from django.dispatch import receiver
from artist.models import Artist
from artist.tasks import create_artist_in_hubspot_task
from legal.tasks import request_contract_signature_task
from chartmetric.tasks import load_chartmetric_ids
from spotify.tasks import load_spotify_artist_data


@receiver(post_save, sender=Artist)
def artist_created(sender, instance, created, **kwargs):
    """ when an artist is created """
    if created:
        # load profile from spotify: synchronous as other requests depend on it
        load_spotify_artist_data(instance.id)

        # request contract signature
        request_contract_signature_task.delay(instance.id)

        # add artist to hubspot
        create_artist_in_hubspot_task.delay(instance.id)
