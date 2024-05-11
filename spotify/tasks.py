
import celery
from django.apps import apps
from acrylic.celery import app
from spotify.engine import spotify_client

@app.task 
def load_spotify_id(track_id, force=False):
        
    Track = apps.get_model('catalog', 'track')

    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        pass
    else:
        if force == True or track.spotify_id == '':
            spotify = spotify_client()
            results = spotify.search(q=f'isrc:{track.isrc}', type='track')
            tracks = [t for t in results['tracks']['items'] if t['external_ids']['isrc'] == track.isrc]
            if len(tracks) > 0:
                # first track where ISRC matches
                track.spotify_id = tracks[0]['id']
                print(f'Track Spotify ID: {track.spotify_id}')
                if not track.artist.spotify_id:
                    artist = track.artist        
                    artist.spotify_id = tracks[0]['artists'][0]['id']
                    artist.save()
                    print(f'Artist Spotify ID: {artist.spotify_id}')
            else:
                print(f'{track.name}, {track.artist.name} - ISRC {track.isrc} No track ID found')
            track.save()
    return True
