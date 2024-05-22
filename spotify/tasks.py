import requests
import celery
from spotify.engine import spotify_client
from django.apps import apps
from django.core.files.base import ContentFile
from acrylic.celery import app


@app.task 
def load_spotify_id(track_id, force=False, load_data=False):
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

        if load_data:
            # call load data
            load_spotify_track_data.delay(track.id)
            
    return True


@app.task
def load_spotify_track_data(track_id, force=False):
    Track = apps.get_model('catalog', 'track')
    try:
        # get track with spotify ID
        track = Track.objects.exclude(spotify_id=None).get(id=track_id)
    except Track.DoesNotExist:
        pass
    else:
        fields = ['cover_image', 'snippet']
        if force == True or any([getattr(track, field) in [None, ''] for field in fields]):
            spotify = spotify_client()
            track_info = spotify.track(f'spotify:track:{track.spotify_id}')
            album_images = track_info['album']['images']

            # load cover art
            if force or not track.cover_image:
                try:
                    image_url = track_info['album']['images'][0]['url']
                except KeyError:
                    image_url = ''
                else:
                    image_file = requests.get(image_url)
                    track.cover_image.save('cover.jpg', ContentFile(image_file.content))

            # load 30 sec preview mp3
            if force or not track.snippet and track_info.get('preview_url', None):
                snippet_file = requests.get(track_info['preview_url'])
                track.snippet.save('snippet.mp3', ContentFile(snippet_file.content))


@app.task
def split_sheet_load_spotify_data_task(split_sheet_id):
    SplitSheet = apps.get_model('legal', 'SplitSheet')

    try:
        # get track with spotify ID
        track = SplitSheet.objects.get(id=split_sheet_id)
    except Track.DoesNotExist:
        pass
    else:
        spotify = spotify_client()
        results = spotify.search(q=f'isrc:{split_sheet.isrc}', type='track')

        tracks = [t for t in results['tracks']['items'] if t['external_ids']['isrc'] == isrc]
        if len(tracks) > 0:
            track_data = tracks[1]
            artist_data = track_data['artists'][0]

            try:
                image_url = track_data['album']['images'][0]['url']
            except KeyError:
                image_url = ''
            else:
                image_file = requests.get(image_url)
                split_sheet.track_cover_image.save('cover.jpg', ContentFile(image_file.content))

            split_sheet.track_name = track_data['name']
            split_sheet.save()
    
    return True
