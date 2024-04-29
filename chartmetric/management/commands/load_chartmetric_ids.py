from catalog.models import *
from chartmetric.engine import *
from django.core.management.base import BaseCommand
from django.conf import settings
from artist.models import Artist
from catalog.models import Track



class Command(BaseCommand):
    help = 'Loads Chartmetrics IDs for Tracks and Artists based on ISRCs'
    def handle(self, *args, **options):
        visited_artist_ids = []

        cm = Chartmetric()
        cm.authenticate()
        for track in Track.objects.filter(chartmetric_id='').order_by('?'):
            data = cm.get_track_artist_ids_from_isrc(track.isrc)
            if len(data['obj']['tracks']) > 0:
                track.chartmetric_id = data['obj']['tracks'][0]['id']
                print(f'Track: {track.chartmetric_id}')
                if not track.artist.chartmetric_id:
                    artist = track.artist
                    artist.chartmetric_id = data['obj']['tracks'][0]['artist'][0]['id']
                    artist.save()
                    print(f'Artist: {artist.chartmetric_id}')
                track.save()

            if track.artist.chartmetric_id not in visited_artist_ids:
                artist = track.artist

                # do same with stats
                stats = cm.get_artist_stats(artist.chartmetric_id)

                # spotify URL
                if stats['spotify']['link']:
                    artist.spotify_url = stats['spotify']['link']
                # spotify followers
                if stats['spotify']['followers']:
                    artist.spotify_followers = stats['spotify']['followers'][0]['value']

                if stats['spotify']['popularity']:
                    artist.spotify_popularity = stats['spotify']['popularity'][0]['value']

                if stats['spotify']['listeners']:
                    artist.spotify_monthly_listeners = stats['spotify']['listeners'][0]['value']

                # instagram URL
                if stats['instagram']['link']:
                    artist.instagram_url = stats['instagram']['link']
                # instagram followers
                if stats['instagram']['followers']:
                    artist.instagram_followers = stats['instagram']['followers'][0]['value']
                
                artist.save()
                visited_artist_ids.append(track.artist.chartmetric_id)
