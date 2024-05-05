import celery
from artist.models import Artist
from catalog.models import Track
from chartmetric.engine import Chartmetric


app = celery.Celery('example')


@app.task
def load_chartmetric_ids(track_id):
    # auth in chartmetric
    cm = Chartmetric()
    cm.authenticate()

    try:
        track = Track.objects.get(chartmetric_id=''):
    except Track.DoesNotExist:
        pass
    else:
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


@app.task
def load_chartmetric_stats(artist_id): 
     # auth in chartmetric
    cm = Chartmetric()
    cm.authenticate()

     try:
        track = Track.objects.get(chartmetric_id=''):
    except Track.DoesNotExist:
        pass
    else:
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

