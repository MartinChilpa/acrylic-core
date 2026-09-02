from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from artist.models import Artist
from catalog.models import Track
from club.models import Club
from license.models import License


class LicenseDownloadedVisibilityTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="club-licenses", email="licenses@example.com")
        self.club = Club.objects.create(club_name="Bay FC", slug="bayfc", user=self.user)
        # Creating an Artist fires artist.signals.artist_created, which calls Spotify
        # synchronously and enqueues a Celery task. Neither is reachable from tests.
        with patch('artist.signals.load_spotify_artist_data'),              patch('artist.signals.request_contract_signature_task.delay'):
            artist = Artist.objects.create(name="Test Artist", country="ES")
        self.track = Track.objects.create(artist=artist, isrc="USE100000002", name="Licensed Track")
        self.license = License.objects.create(club=self.club, track=self.track)
        self.client.force_authenticate(self.user)

    def test_list_hides_licenses_until_the_track_is_downloaded(self):
        response = self.client.get("/api/v1/my-club/licenses/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

        self.license.mark_downloaded()

        response = self.client.get("/api/v1/my-club/licenses/")
        self.assertEqual(len(response.json()), 1)
        self.assertTrue(response.json()[0]["downloaded"])

    def test_list_accepts_downloaded_query_param(self):
        pending = self.client.get("/api/v1/my-club/licenses/?downloaded=false")
        self.assertEqual(len(pending.json()), 1)

        every = self.client.get("/api/v1/my-club/licenses/?downloaded=all")
        self.assertEqual(len(every.json()), 1)

    def test_mark_downloaded_endpoint_is_idempotent(self):
        url = f"/api/v1/my-club/licenses/{self.license.uuid}/mark-downloaded/"

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["downloaded"])

        self.license.refresh_from_db()
        first_downloaded_at = self.license.downloaded_at
        self.assertIsNotNone(first_downloaded_at)

        again = self.client.post(url)
        self.assertEqual(again.status_code, 200)
        self.license.refresh_from_db()
        self.assertEqual(self.license.downloaded_at, first_downloaded_at)

    def test_mark_downloaded_is_scoped_to_the_owning_club(self):
        other_user = get_user_model().objects.create(username="other-club", email="other@example.com")
        Club.objects.create(club_name="Monaco", slug="monaco", user=other_user)
        self.client.force_authenticate(other_user)

        response = self.client.post(f"/api/v1/my-club/licenses/{self.license.uuid}/mark-downloaded/")
        self.assertEqual(response.status_code, 404)
        self.license.refresh_from_db()
        self.assertFalse(self.license.downloaded)
