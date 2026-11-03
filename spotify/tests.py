from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from spotipy.exceptions import SpotifyException

from artist.models import Artist
from catalog.models import Track

from spotify.tasks import load_spotify_track_data


class SpotifyTrackDataTests(TestCase):
    def test_load_spotify_track_data_overwrites_name_from_spotify(self):
        with (
            patch("artist.signals.load_spotify_artist_data", return_value=True),
            patch("artist.signals.request_contract_signature_task.delay", return_value=None),
        ):
            artist = Artist.objects.create(name="Some Artist")
        with (
            patch("catalog.models.load_spotify_id.delay", return_value=None),
            patch("catalog.models.load_chartmetric_ids.delay", return_value=None),
        ):
            track = Track.objects.create(
                artist=artist,
                isrc="USEE10001993",
                spotify_id="dummy",
                name="Old Name",
            )

        class FakeSpotify:
            def track(self, _):
                return {"name": "New Name", "album": {"images": []}, "preview_url": None}

        with patch("spotify.tasks.spotify_client", return_value=FakeSpotify()):
            load_spotify_track_data(track.id, force=False)

        track.refresh_from_db()
        self.assertEqual(track.name, "New Name")


class SpotifyTrackSearchTests(TestCase):
    url = "/api/v1/spotify/search/"

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username="searcher", password="p")
        self.client.force_authenticate(user=self.user)

    def _fake_spotify(self):
        spotify = MagicMock()
        spotify.search.return_value = {
            "tracks": {
                "items": [
                    {
                        "id": "abc123",
                        "name": "Al Diablo Lo Nuestro",
                        "artists": [{"name": "Espinoza Paz"}, {"name": "Guest"}],
                        "album": {
                            "images": [
                                {"url": "https://i.scdn.co/640.jpg", "width": 640, "height": 640},
                                {"url": "https://i.scdn.co/300.jpg", "width": 300, "height": 300},
                                {"url": "https://i.scdn.co/64.jpg", "width": 64, "height": 64},
                            ]
                        },
                        "external_urls": {"spotify": "https://open.spotify.com/track/abc123"},
                        "external_ids": {"isrc": "TCADI1790022"},
                        "duration_ms": 201000,
                    },
                    {
                        "id": "def456",
                        "name": "No Art",
                        "artists": [{"name": "Someone"}],
                        "album": {"images": []},
                        "external_urls": {"spotify": "https://open.spotify.com/track/def456"},
                        "external_ids": {},
                        "duration_ms": 1000,
                    },
                ]
            }
        }
        return spotify

    def test_search_returns_results(self):
        spotify = self._fake_spotify()
        with patch("spotify.views.spotify_client", return_value=spotify):
            res = self.client.get(self.url, {"q": "  al diablo  ", "limit": 50})

        self.assertEqual(res.status_code, 200)
        spotify.search.assert_called_once_with(q="al diablo", type="track", limit=10)
        results = res.json()["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], {
            "name": "Al Diablo Lo Nuestro",
            "artist": "Espinoza Paz, Guest",
            "image": "https://i.scdn.co/64.jpg",
            "spotify_url": "https://open.spotify.com/track/abc123",
            "spotify_id": "abc123",
            "isrc": "TCADI1790022",
            "duration": 201000,
        })
        self.assertEqual(results[1]["image"], "")
        self.assertIsNone(results[1]["isrc"])

    def test_search_default_limit_and_cache(self):
        spotify = self._fake_spotify()
        with patch("spotify.views.spotify_client", return_value=spotify):
            first = self.client.get(self.url, {"q": "Al Diablo"})
            second = self.client.get(self.url, {"q": "al   diablo"})

        self.assertEqual(first.json(), second.json())
        spotify.search.assert_called_once_with(q="Al Diablo", type="track", limit=5)

    def test_short_query_skips_spotify(self):
        with patch("spotify.views.spotify_client") as client:
            res = self.client.get(self.url, {"q": " a "})

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"results": []})
        client.assert_not_called()

    def test_spotify_error_returns_503(self):
        spotify = MagicMock()
        spotify.search.side_effect = SpotifyException(429, -1, "rate limited secret-stuff")
        with patch("spotify.views.spotify_client", return_value=spotify):
            res = self.client.get(self.url, {"q": "al diablo"})

        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json(), {"detail": "Spotify search unavailable"})

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        with patch("spotify.views.spotify_client") as client:
            res = self.client.get(self.url, {"q": "al diablo"})

        self.assertIn(res.status_code, (401, 403))
        client.assert_not_called()
