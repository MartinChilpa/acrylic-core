from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from artist.models import Artist
from catalog.models import Track
from club.models import Club
from legal.models import License, LicenseHistory


class LicenseModelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="club-user", email="club@example.com", password="pass")

        with patch("club.signals.send_registration_invite", return_value=None):
            self.club = Club.objects.create(user=self.user, club_name="Club One")

        with (
            patch("artist.signals.load_spotify_artist_data", return_value=True),
            patch("artist.signals.request_contract_signature_task.delay", return_value=None),
        ):
            self.artist = Artist.objects.create(name="Artist One")

        with (
            patch("catalog.models.load_spotify_id.delay", return_value=None),
            patch("catalog.models.load_chartmetric_ids.delay", return_value=None),
        ):
            self.track = Track.objects.create(artist=self.artist, isrc="USEE10002001", name="Track One")

    def test_license_creates_initial_history(self):
        license_obj = License.objects.create(
            club=self.club,
            track=self.track,
            requested_by=self.user,
            price="100.00",
        )

        self.assertEqual(license_obj.status, License.Status.IN_PROGRESS)
        history = license_obj.history.order_by("created")
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().from_status, "")
        self.assertEqual(history.first().to_status, License.Status.IN_PROGRESS)
        self.assertEqual(history.first().changed_by, self.user)

    def test_license_status_change_adds_history_entry(self):
        license_obj = License.objects.create(
            club=self.club,
            track=self.track,
            requested_by=self.user,
            price="100.00",
        )

        license_obj.status = License.Status.COMPLETE
        license_obj.save(status_changed_by=self.user, history_notes="paid")

        history = license_obj.history.order_by("created")
        self.assertEqual(history.count(), 2)
        self.assertEqual(history.last().from_status, License.Status.IN_PROGRESS)
        self.assertEqual(history.last().to_status, License.Status.COMPLETE)
        self.assertEqual(history.last().changed_by, self.user)
        self.assertEqual(history.last().notes, "paid")
