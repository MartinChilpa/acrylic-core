from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from label.models import Label
from artist.models import Artist
from rest_framework.test import APIClient


class SaveArtistsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_user(username="label-user", email="label@example.com", password="pass")
        self.client.force_authenticate(user=user)
        self.user = user

        with patch("club.signals.send_registration_invite", return_value=None):
            self.label = Label.objects.create(user=user, label_name="My Label")

    def test_accepts_artists_alias_and_name_only(self):
        res = self.client.post(
            "/api/v1/ingestion/save_artists/",
            {"artists": [{"name": "Artist One"}, {"name": "Artist Two"}]},
            format="json",
        )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["created"], 2)
        self.assertEqual(Artist.objects.filter(label=self.label).count(), 2)

    def test_updates_existing_artist_when_spotify_url_is_present(self):
        with (
            patch("artist.signals.load_spotify_artist_data", return_value=True),
            patch("artist.signals.request_contract_signature_task.delay", return_value=None),
        ):
            artist = Artist.objects.create(label=self.label, name="Artist One")

        res = self.client.post(
            "/api/v1/ingestion/save_artists/",
            {"artists_with_spotify": [{"name": "Artist One", "spotify_url": "https://open.spotify.com/artist/1234567890ABCDE1234567"}]},
            format="json",
        )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["updated"], 1)
        artist.refresh_from_db()
        self.assertEqual(artist.spotify_url, "https://open.spotify.com/artist/1234567890ABCDE1234567")
