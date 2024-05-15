from datetime import datetime
import dateutil
from django.core.management.base import BaseCommand
from django.conf import settings
from spotify.engine import spotify_client
from artist.models import Artist
from catalog.models import Track


class Command(BaseCommand):
    help = 'Imports tracks and artists from a specified Spotify playlist'
    # https://open.spotify.com/playlist/2fuHQ3Dfe0xSbr5sibd1lV
    
    #from catalog.models import *
    #import time
    #for t in Track.objects.filter(spotify_id='').order_by('?'):
    #    t._update_spotify_id()
    #    time.sleep(3)
        
    def add_arguments(self, parser):
        parser.add_argument('playlist_id', type=str, help='Spotify Playlist ID')

    def handle(self, *args, **options):
        playlist_id = options['playlist_id']
        #token = self.get_spotify_token()
        sp = self.get_spotify_instance()
        tracks_data = self.get_playlist_tracks(sp, playlist_id)
        self.load_tracks_and_artists(tracks_data)

    def get_spotify_instance(self):
        return spotify_client()
        results = spotify.search(q=f'isrc:{self.isrc}', type='track', market='ES')

    def get_playlist_tracks(self, sp, playlist_id):
        results = sp.playlist_tracks(playlist_id)
        tracks = []
        while results['next']:
            tracks.extend(results['items'])
            results = sp.next(results)
        tracks.extend(results['items'])
        return tracks

    def load_tracks_and_artists(self, tracks_data):
        for track_item in tracks_data:
            track_info = track_item['track']
            if not track_info:
                continue  # skip local or missing tracks
            artist_info = track_info['artists'][0]  # Assuming the first artist primarily
            main_artists = []
            
            for artist_info in track_info['artists']:
                artist, _ = Artist.objects.update_or_create(
                    spotify_url=f"https://open.spotify.com/artist/{artist_info['id']}",
                    defaults={
                        'spotify_id': artist_info['id'],
                        'name': artist_info['name'],
                        'bio': artist_info.get('biography', ''),
                        'spotify_url': artist_info['external_urls'].get('spotify'),
                        'instagram_url': artist_info['external_urls'].get('instagram', ''),
                        'youtube_url': artist_info['external_urls'].get('youtube', ''),
                        'twitter_url': artist_info['external_urls'].get('twitter', ''),
                        'facebook_url': artist_info['external_urls'].get('facebook', ''),
                        # Add more fields here as needed
                    }
                )
                main_artists.append(artist)

                # Adding genre and tag information
                #for genre_name in track_info['genres']:
                #    artist.tags.add(genre_name)  # Assuming 'tags' can accept genre names directly
            
            # parse release date
            default_date = datetime(datetime.now().year, 1, 1)
            release_date = dateutil.parser.parse(track_info['album']['release_date'], default=default_date)

            track, _ = Track.objects.get_or_create(
                spotify_id=track_info['id'],
                name=track_info['name'],
                artist=artist,
                duration=int(track_info['duration_ms'] / 1000),
                released=release_date,
                #spotify_url=f"https://open.spotify.com/track/{track_info['id']}",
                isrc=track_info['external_ids'].get('isrc', '')
            )

            # Add additional main artists
            if len(main_artists) > 1:
                track.additional_main_artists.set(main_artists[1:])  # Exclude the primary artist already set

            print(f"Loaded: {track.name} by {artist.name}")
