import requests
import json
from django.conf import settings


API_BASE_URL = 'https://api.chartmetric.com/api/'


class Chartmetric():
    refresh_token = None
    auth_token = None

    def __init__(self, refresh_token=None):
       self.refresh_token = refresh_token or settings.CHARTMETRIC_REFRESH_TOKEN

    def _request(self, method, path, data=None):
        url = f'{API_BASE_URL}{path}'
        headers = {
            'Content-Type': 'application/json'
        }
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'

        if data:
            data = json.dumps(data)
        response = getattr(requests, method)(url, data, headers=headers)
        response_data = response.json()
        print(response_data)
        return response_data

    def authenticate(self):
        data = {
            'refreshtoken': self.refresh_token
        }
        response = self._request('post', 'token', data)
        # POST request to get the access token
        self.auth_token = response['token']
        print(self.auth_token)

    def get_track_artist_ids_from_isrc(self, isrc):
        path = f'search?q={isrc}&type=tracks&limit=1'
        return self._request('get', path)
    
    def get_artist_id_from_spotify(self, spotify_id):
        path = f'search?q={spotify_id}&type=artists&limit=1'
        return self._request('get', path)

    #def get_track_stats(self, track_id):
    #    path = f'track/{track_id}/{type}/charts'
    #    print(f'GET {path}')
    #    data[source] = self._request('get', path)['obj']

    def get_artist_stats(self, artist_id, sources=['instagram', 'spotify']):
        # https://api.chartmetric.com/api/artist/439/stat/spotify

        """
        GET artist/5398878/stat/instagram?latest=true
        'obj': {'link': 'https://www.instagram.com/chillandgo_/', 'followers': [{'weekly_diff': -36, 'weekly_diff_percent': -0.1975, 'monthly_diff': -170, 'monthly_diff_percent': -0.9251, 'value': 18188, 'timestp': '2024-04-27T00:00:00.000Z', 'diff': None}]}}
        
        GET artist/5398878/stat/spotify?latest=true
        {'obj': {'link': 'https://open.spotify.com/artist/6EE1OjZRlv4jJJ1bUUvp5h', 'followers': [{'weekly_diff': None, 'weekly_diff_percent': None, 'monthly_diff': 160, 'monthly_diff_percent': 5.7143, 'value': 2960, 'timestp': '2024-04-24T00:00:00.000Z', 'diff': None}], 'popularity': [{'weekly_diff': None, 'weekly_diff_percent': None, 'monthly_diff': 0, 'monthly_diff_percent': 0, 'value': 32, 'timestp': '2024-04-24T00:00:00.000Z'}], 'listeners': [{'weekly_diff': None, 'weekly_diff_percent': None, 'monthly_diff': 19247, 'monthly_diff_percent': 32.1008, 'value': 79205, 'timestp': '2024-04-24T00:00:00.000Z', 'diff': None}], 'followers_to_listeners_ratio': [{'weekly_diff': None, 'weekly_diff_percent': None, 'monthly_diff': -0.009327999996, 'monthly_diff_percent': -19.9747317844, 'value': '3.74', 'timestp': '2024-04-24T00:00:00.000Z'}]}}
        
        GET artist/5398878/stat/tiktok?latest=true
        {'obj': {'link': None, 'followers': [], 'likes': []}}
        

        #sources = [
        #    'spotify', 'deezer', 'facebook', 'twitter', 'instagram', 'youtube_channel', 'youtube_artist',
        #    'wikipedia', 'bandsintown', 'soundcloud', 'tiktok', 'twitch'
        #]
        """
        print(sources)
        data = {}
        for source in sources:
            path = f'artist/{artist_id}/stat/{source}?latest=true'
            print(f'GET {path}')
            data[source] = self._request('get', path)['obj']
        return data

    def get_artist_ids(self, artist_id):
        return self._request('get', f'artist/chartmetric/{artist_id}/get-ids')
    
        #        "artist_name": "Hailee Steinfeld",
        #        "spotify_artist_id": "5p7f24Rk5HkUZsaS3BLG5F",
        #        "itunes_artist_id": 417571723,
        #        "deezer_artist_id": "5961630",
        #        "amazon_artist_id": "B00L4I14C0",
        #        "youtube_channel_id": "UCWfytcGFwPSMwvP5HYuXGqw",
        #        "tivo_artist_id": "MN0003276047"
        #    },
