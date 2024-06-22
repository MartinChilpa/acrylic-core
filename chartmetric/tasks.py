import time
import celery
from django.apps import apps
from chartmetric.engine import Chartmetric
from acrylic.celery import app


@app.task
def load_chartmetric_artist_ids(artist_id, force=False):
    # NOT USED!
    Artist = apps.get_model('artist', 'Artist')

    try:
        artist = Artist.objects.get(id=artist_id)
    except Artist.DoesNotExist:
        pass
    else:
        if (force == True or artist.chartmetric_id == ''):
            # auth in chartmetric
            cm = Chartmetric()
            cm.authenticate()
            # chartmetric 1rps
            time.sleep(1.5)
            data = cm.get_artist_id_from_spotify(artist.name)
            if 'error' not in data and data.get('obj'):
                if len(data['obj']['artists']) > 0:
                    artist_data = data['obj']['artists'][0]
                    # store chartmetric id
                    artist.chartmetric_id = artist_data['id']
                    print(f'Artist: {artist.chartmetric_id}')
                    track.save()
    return True


@app.task
def load_chartmetric_ids(track_id, force=False):
    Track = apps.get_model('catalog', 'track')

    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        pass
    else:
        if force == True or track.chartmetric_id == '':
            # auth in chartmetric
            cm = Chartmetric()
            cm.authenticate()
            # chartmetric 1rps
            time.sleep(1.5)
            data = cm.get_track_artist_ids_from_isrc(track.isrc)
            if 'error' not in data and data.get('obj'):
                if len(data['obj']['tracks']) > 0:
                    track_data = data['obj']['tracks'][0]
                    if track_data['isrc'] == track.isrc:
                        # ensure that ISRC matches
                        track.chartmetric_id = track_data['id']
                        print(f'Track: {track.chartmetric_id}')
                        if not track.artist.chartmetric_id:
                            artist = track.artist
                            artist.chartmetric_id = track_data['artist'][0]['id']
                            artist.save()
                            print(f'Artist: {artist.chartmetric_id}')
                        track.save()
    return True


@app.task
def load_chartmetric_stats(track_id): 
    Track = apps.get_model('catalog', 'track')

    # auth in chartmetric
    cm = Chartmetric()
    cm.authenticate()

    # chartmetric 1rps
    time.sleep(1.5)
    
    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        pass
    else:
        stats = cm.get_artist_stats(artist.chartmetric_id)

        if 'error' not in data:

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

    return True