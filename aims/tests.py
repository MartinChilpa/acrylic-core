from unittest.mock import patch

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from rest_framework.test import APIClient

from artist.models import Artist
from catalog.models import Track
from catalog.models import Price


class AimsWebhookTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _create_track(self):
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
                name="Track",
            )
        return track

    def test_webhook_marks_finished(self):
        track = self._create_track()
        self.assertNotEqual(track.aims_status, Track.AimsStatus.FINISHED)

        res = self.client.post(
            "/aims-webhook",
            {"id_client": str(track.aims_id), "status": "finished"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)

        track.refresh_from_db()
        self.assertEqual(track.aims_status, Track.AimsStatus.FINISHED)

    @override_settings(AIMS_WEBHOOK_SECRET="sekret")
    def test_webhook_requires_secret_when_configured(self):
        track = self._create_track()

        res = self.client.post(
            "/aims-webhook",
            {"id_client": str(track.aims_id), "status": "finished"},
            format="json",
        )
        self.assertEqual(res.status_code, 401)

        res = self.client.post(
            "/aims-webhook",
            {"id_client": str(track.aims_id), "status": "finished"},
            format="json",
            HTTP_X_AIMS_WEBHOOK_SECRET="sekret",
        )
        self.assertEqual(res.status_code, 200)


class AimsSimplifyTests(TestCase):
    def test_simplify_defaults_release_year_2021(self):
        from aims.views import _simplify_aims_item

        out = _simplify_aims_item({"track_name": "X", "artist_canonical": "Y"})
        self.assertEqual(out["release_year"], 2021)

    def test_simplify_includes_track_virality_from_catalog(self):
        from aims.views import _simplify_aims_item

        with (
            patch("artist.signals.load_spotify_artist_data", return_value=True),
            patch("artist.signals.request_contract_signature_task.delay", return_value=None),
        ):
            artist = Artist.objects.create(name="Some Artist", country="AR")

        with (
            patch("catalog.models.load_spotify_id.delay", return_value=None),
            patch("catalog.models.load_chartmetric_ids.delay", return_value=None),
        ):
            track = Track.objects.create(
                artist=artist,
                isrc="USEE10001994",
                name="Track",
                virality=98.7,
            )

        out = _simplify_aims_item({"id_client": track.aims_id, "track_name": "X", "artist_canonical": "Y"})
        self.assertEqual(out["track_virality"], 98.7)
        self.assertEqual(out["artist_country_code2"], "AR")

    def test_simplify_includes_track_price(self):
        from aims.views import _simplify_aims_item

        with (
            patch("artist.signals.load_spotify_artist_data", return_value=True),
            patch("artist.signals.request_contract_signature_task.delay", return_value=None),
        ):
            artist = Artist.objects.create(name="Some Artist")

        price = Price.objects.create(name="P1", description="", max_artist_tracks=0, default=False, active=True, order=0)

        with (
            patch("catalog.models.load_spotify_id.delay", return_value=None),
            patch("catalog.models.load_chartmetric_ids.delay", return_value=None),
        ):
            track = Track.objects.create(
                artist=artist,
                isrc="USEE10001996",
                name="Track",
                price=price,
            )

        out = _simplify_aims_item({"id_client": track.aims_id, "track_name": "X", "artist_canonical": "Y"})
        self.assertEqual(out["price_id"], price.id)
        self.assertEqual(out["price_uuid"], str(price.uuid))

    @override_settings(CHARTMETRIC_USE_DUMMY_FALLBACKS=True)
    def test_simplify_applies_dummy_chartmetric_fallbacks_when_empty(self):
        from aims.views import _simplify_aims_item

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
                isrc="USEE10001995",
                name="Track",
                virality=None,
            )

        out = _simplify_aims_item({"id_client": track.aims_id, "track_name": "X", "artist_canonical": "Y"})
        self.assertAlmostEqual(out["track_virality"], 53.2, places=6)
        self.assertEqual(out["instagram_followers"], 45123)
        self.assertEqual(out["spotify_followers"], 34412)
        self.assertEqual(out["tiktok_followers"], 14231)
        self.assertEqual(out["youtube_followers"], 32123)
        self.assertEqual(out["chartmetric_instagram_demographics"][0]["timestp"], "2025-08-07")
        self.assertEqual(out["chartmetric_instagram_top_cities"][0]["city_name"], "Los Angeles")
        self.assertEqual(out["chartmetric_instagram_top_countries"][0]["code2"], "US")
        self.assertAlmostEqual(out["chartmetric_instagram_sports_fit_percent"], 33.33, places=2)


class AimsSpotifySchemaTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(username="u", password="p")
        self.client.force_authenticate(user=self.user)

    def test_similarity_spotify_response_has_seed_track_and_matches(self):
        from aims.views import _simplify_aims_item
        from rest_framework.response import Response

        with (
            patch("artist.signals.load_spotify_artist_data", return_value=True),
            patch("artist.signals.request_contract_signature_task.delay", return_value=None),
        ):
            artist = Artist.objects.create(name="Vicente Fernández", country="MX", chartmetric_instagram_sports_fit_percent=47.1)

        price = Price.objects.create(name="P1", description="", max_artist_tracks=0, default=False, active=True, order=0)

        with (
            patch("catalog.models.load_spotify_id.delay", return_value=None),
            patch("catalog.models.load_chartmetric_ids.delay", return_value=None),
        ):
            seed = Track.objects.create(
                artist=artist,
                isrc="MXF010700413",
                name="Estos Celos",
                spotify_id="6u6kH7V7Tx5xDJtF82vVw0",
                virality=94.8,
                price=price,
            )
            match_track = Track.objects.create(
                artist=artist,
                isrc="USEE10001997",
                name="Other",
            )

        match_item = _simplify_aims_item(
            {
                "id_client": match_track.aims_id,
                "track_name": "Other",
                "artist_canonical": "Vicente Fernández",
                "score": 0.93,
            }
        )

        def _fake_aims_query(self, *, link, page=1, page_size=20, highlights=True, detailed=True, request=None):
            return Response({"count": 1, "results": [match_item]}, status=200)

        class _Sp:
            def track(self, spotify_id):
                return {
                    "name": "Estos Celos",
                    "artists": [{"name": "Vicente Fernández"}],
                    "album": {"images": [{"url": "https://img"}]},
                    "external_ids": {"isrc": "MXF010700413"},
                }

        with (
            patch("aims.views.spotify_client", return_value=_Sp()),
            patch("aims.views.SimilarityViewSet._aims_query_by_url", new=_fake_aims_query),
        ):
            res = self.client.post(
                "/api/v1/aims/similarity/",
                {"spotify_url": "https://open.spotify.com/track/6u6kH7V7Tx5xDJtF82vVw0", "page": 1, "page_size": 10},
                format="json",
            )

        self.assertEqual(res.status_code, 200)
        payload = res.json()

        self.assertEqual(payload["spotify"]["spotify_id"], "6u6kH7V7Tx5xDJtF82vVw0")
        self.assertTrue(payload["seed_track"]["in_catalog"])
        self.assertEqual(payload["seed_track"]["track"]["track_id"], seed.id)
        self.assertEqual(payload["seed_track"]["track"]["price_id"], price.id)
        self.assertAlmostEqual(payload["seed_track"]["track"]["track_virality"], 94.8, places=6)
        self.assertAlmostEqual(payload["seed_track"]["track"]["audience_sport_fit_percent"], 47.1, places=1)
        # Seed track includes the same fields as results items.
        self.assertIn("spotify_followers", payload["seed_track"]["track"])
        self.assertIn("chartmetric_instagram_top_countries", payload["seed_track"]["track"])
        self.assertEqual(payload["seed_track"]["track"]["artist_country_code2"], "MX")

        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["track_id"], match_track.id)
        self.assertAlmostEqual(payload["results"][0]["match_score"], 0.93, places=2)
        self.assertEqual(payload["results"][0]["artist_country_code2"], "MX")
