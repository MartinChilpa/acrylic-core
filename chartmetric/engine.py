import requests
import json
import logging
import time
from urllib.parse import urlencode
from django.conf import settings


API_BASE_URL = 'https://api.chartmetric.com/api/'

logger = logging.getLogger(__name__)


class Chartmetric():
    refresh_token = None
    auth_token = None

    def __init__(self, refresh_token=None):
       self.refresh_token = refresh_token or settings.CHARTMETRIC_REFRESH_TOKEN

    def _request(self, method, path, data=None, timeout=None):
        url = f'{API_BASE_URL}{path}'
        headers = {
            'Content-Type': 'application/json'
        }
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'

        body = json.dumps(data) if data is not None else None
        # Allow overriding request timeout from Django settings.
        # When unset, default to 60s read timeout to accommodate heavier endpoints.
        effective_timeout = timeout
        if effective_timeout is None:
            effective_timeout = getattr(settings, "CHARTMETRIC_REQUEST_TIMEOUT", 60)
        # Use (connect, read) timeouts to fail fast on network issues but allow slow responses.
        if isinstance(effective_timeout, (int, float)):
            effective_timeout = (10, effective_timeout)

        try:
            response = requests.request(method, url, headers=headers, data=body, timeout=effective_timeout)
        except requests.exceptions.Timeout as exc:
            return {
                "error": "timeout",
                "detail": str(exc),
            }
        except requests.exceptions.RequestException as exc:
            return {
                "error": "request_exception",
                "detail": str(exc),
            }
        try:
            response_data = response.json()
        except ValueError:
            # Chartmetric can occasionally return non-JSON (e.g. HTML errors, empty body).
            return {
                "error": "non_json_response",
                "status_code": response.status_code,
                "text": response.text[:500],
            }
        if response.status_code >= 400:
            # Keep the parsed body around (Chartmetric often returns JSON errors),
            # but normalize into a consistent error envelope.
            return {
                "error": "http_error",
                "status_code": response.status_code,
                "body": response_data,
            }
        # Avoid printing potentially sensitive payloads (tokens, ids) into Celery logs.
        return response_data

    def authenticate(self):
        data = {
            'refreshtoken': self.refresh_token
        }
        response = self._request('post', 'token', data)
        # POST request to get the access token
        self.auth_token = response['token']
        logger.info("Chartmetric authenticated (token received).")

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

    def get_artist_stats(self, artist_id, sources=None, sleep_seconds=1.5):
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
        sources = sources or ['instagram', 'spotify', 'tiktok', 'youtube_channel']

        data = {}
        for idx, source in enumerate(sources):
            # Chartmetric is strict about RPS. Without throttling, some sources
            # can randomly come back empty/errored (429) while others succeed.
            if idx and sleep_seconds:
                time.sleep(sleep_seconds)
            path = f'artist/{artist_id}/stat/{source}?latest=true'
            res = self._request('get', path)
            data[source] = res.get('obj') if isinstance(res, dict) else None
        return data

    def get_artist_ids(self, artist_id):
        return self._request('get', f'artist/chartmetric/{artist_id}/get-ids')

    def get_social_audience_stats(
        self,
        artist_id,
        *,
        domain='instagram',
        audience_type='followers',
        stats_type='country',
        since='2021-09-13',
        until=None,
        limit=3,
    ):
        """
        Wrapper for:
        /api/artist/{id}/social-audience-stats?domain=instagram&audienceType=followers&statsType=country&since=YYYY-MM-DD&limit=3

        Returns the raw API response dict.
        """
        params = {
            'domain': domain,
            'audienceType': audience_type,
            'statsType': stats_type,
        }
        if since:
            params['since'] = since
        if until:
            params['until'] = until
        if limit is not None:
            params['limit'] = int(limit)

        path = f"artist/{artist_id}/social-audience-stats?{urlencode(params)}"
        return self._request('get', path)

    def get_top_countries_instagram(self, artist_id, *, since='2021-09-13', limit=3):
        """
        Returns list of dicts: [{"name": ..., "code2": ..., "weights": ...}, ...]
        """
        res = self.get_social_audience_stats(
            artist_id,
            domain='instagram',
            audience_type='followers',
            stats_type='country',
            since=since,
            limit=limit,
        )
        obj = (res or {}).get('obj') if isinstance(res, dict) else None
        return obj or []

    def get_top_cities_instagram(self, artist_id, *, since='2021-09-13', limit=3):
        """
        Returns list of dicts: [{"city_name": ..., "code2": ..., "weights": ...}, ...]
        """
        res = self.get_social_audience_stats(
            artist_id,
            domain='instagram',
            audience_type='followers',
            stats_type='city',
            since=since,
            limit=limit,
        )
        obj = (res or {}).get('obj') if isinstance(res, dict) else None
        return obj or []

    def get_demographics_instagram(self, artist_id, *, since='2021-09-13', limit=1):
        """
        Returns the raw obj for statsType=demographic (usually a list with one dict).
        """
        res = self.get_social_audience_stats(
            artist_id,
            domain='instagram',
            audience_type='followers',
            stats_type='demographic',
            since=since,
            limit=limit,
        )
        obj = (res or {}).get('obj') if isinstance(res, dict) else None
        return obj or []
    
        #        "artist_name": "Hailee Steinfeld",
        #        "spotify_artist_id": "5p7f24Rk5HkUZsaS3BLG5F",
        #        "itunes_artist_id": 417571723,
        #        "deezer_artist_id": "5961630",
        #        "amazon_artist_id": "B00L4I14C0",
        #        "youtube_channel_id": "UCWfytcGFwPSMwvP5HYuXGqw",
        #        "tivo_artist_id": "MN0003276047"
        #    },
