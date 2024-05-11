import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from django.conf import settings


def spotify_client():
    client_id = settings.SPOTIFY_CLIENT_ID
    client_secret = settings.SPOTIFY_CLIENT_SECRET
    spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
    return spotify
