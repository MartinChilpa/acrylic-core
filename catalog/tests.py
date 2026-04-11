from unittest.mock import patch

import tempfile

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from artist.models import Artist
from catalog.models import Track
from catalog.tasks import upload_track_to_aims
from label.models import Label
from rest_framework.test import APIClient


class CatalogViralityTests(TestCase):
    _MEDIA_ROOT = tempfile.mkdtemp(prefix="acrylic-test-media-")

    @override_settings(
        AIMS_CLIENT_ID="x",
        AIMS_API_SECRET="y",
        AIMS_WEBHOOK_URL="",
        MEDIA_ROOT=_MEDIA_ROOT,
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        },
    )
    def test_upload_track_to_aims_saves_virality_when_chartmetric_id_present(self):
        with (
            patch("artist.signals.load_spotify_artist_data", return_value=True),
            patch("artist.signals.request_contract_signature_task.delay", return_value=None),
        ):
            artist = Artist.objects.create(name="Some Artist")

        with (
            patch("catalog.models.load_spotify_id.delay", return_value=None),
            patch("catalog.models.load_chartmetric_ids.delay", return_value=None),
        ):
            track = Track.objects.create(artist=artist, isrc="USEE10001993", name="Track", chartmetric_id="123")

        track.file_mp3.save("track.mp3", ContentFile(b"abc"), save=True)

        captured = {}

        def _post(url, headers=None, data=None, files=None, timeout=None):
            captured["url"] = url
            captured["data"] = data
            captured["headers"] = headers
            captured["timeout"] = timeout

            class _Resp:
                status_code = 200

                def json(self):
                    return {"ok": True}

            return _Resp()

        with (
            patch("catalog.tasks.requests.post", side_effect=_post),
            patch("chartmetric.engine.Chartmetric.authenticate", return_value=True),
            patch("chartmetric.engine.Chartmetric.get_track_virality", return_value=12.34),
        ):
            ok = upload_track_to_aims(track.id)
            self.assertTrue(ok)

        self.assertEqual((captured.get("data") or {}).get("release_year"), 2021)

        track.refresh_from_db()
        self.assertAlmostEqual(track.virality, 12.34, places=6)


class CatalogIngestionAsyncTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(username="label_user", password="p")
        self.label = Label.objects.create(user=self.user, label_name="My Label")
        with (
            patch("artist.signals.load_spotify_artist_data", return_value=True),
            patch("artist.signals.request_contract_signature_task.delay", return_value=None),
        ):
            self.artist = Artist.objects.create(name="A", label=self.label, spotify_id="artist123")
        self.client.force_authenticate(user=self.user)

    def test_ingestion_save_tracks_enqueues_tasks(self):
        class _Async:
            id = "task-1"

        with (
            patch("catalog.tasks.ingest_track_audio_from_url.delay", return_value=_Async()),
            patch("catalog.models.load_spotify_id.delay", return_value=None),
            patch("catalog.models.load_chartmetric_ids.delay", return_value=None),
        ):
            res = self.client.post(
                "/api/v1/ingestion/save_tracks/",
                {
                    "tracks": [
                        {"mp3": "https://example.com/a.mp3", "isrc": "MXF148700181", "artist_spotify_id": "artist123", "name": "T1"},
                        {"mp3": "https://example.com/b.mp3", "isrc": "MXF148700182", "artist_spotify_id": "artist123", "name": "T2"},
                    ]
                },
                format="json",
            )

        self.assertEqual(res.status_code, 202)
        payload = res.json()
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["enqueued"], 2)
        self.assertEqual(payload["mode"], "async")
        self.assertEqual(len(payload["results"]), 2)
        self.assertEqual(payload["results"][0]["task_id"], "task-1")
