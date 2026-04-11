from unittest.mock import patch

from django.test import TestCase

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
