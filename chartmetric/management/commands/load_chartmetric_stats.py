from catalog.models import *
from django.core.management.base import BaseCommand
from django.conf import settings
from artist.models import Artist
from catalog.models import Track
from chartmetric.tasks import load_chartmetric_stats



class Command(BaseCommand):
    help = 'Loads Chartmetrics IDs for Tracks and Artists based on ISRCs'
    def handle(self, *args, **options):
        for artist in Artist.objects.exclude(chartmetric_id='').filter(spotify_followers=0).order_by('?'):
            load_chartmetric_stats.delay(artist.id)
