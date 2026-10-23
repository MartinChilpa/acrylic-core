from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from artist.models import Artist
from catalog.models import Track
from club.models import Club, Player, TrackPublishedLink


class TrackFavoriteEndpointTests(APITestCase):
    def test_toggle_and_list_track_favorites_for_club(self):
        user = get_user_model().objects.create(username="club-admin", email="club@example.com")
        club = Club.objects.create(club_name="CF Montreal", slug="cfmontreal", user=user)
        artist = Artist.objects.create(
            name="Test Artist",
            country="ES",
            spotify_followers=1200,
            instagram_followers=800,
            chartmetric_instagram_sports_fit_percent=42.5,
        )
        track = Track.objects.create(
            artist=artist,
            isrc="USE100000001",
            name="Saved Track",
            file_wav="tracks/saved-track.wav",
            waveform="tracks/saved-track.json",
            virality=67.5,
        )

        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/v1/my-club/favorites/toggle/",
            {"track_uuid": str(track.uuid)},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_favorited"])
        self.assertEqual(club.track_favorites.count(), 1)

        list_response = self.client.get("/api/v1/my-club/favorites/")
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["track_uuid"], str(track.uuid))
        persisted_track = payload["results"][0]["track"]
        self.assertEqual(persisted_track["track_uuid"], str(track.uuid))
        self.assertTrue(urlparse(persisted_track["file_wav"]).path.endswith("tracks/saved-track.wav"))
        self.assertTrue(urlparse(persisted_track["waveform"]).path.endswith("tracks/saved-track.json"))
        self.assertEqual(persisted_track["spotify_followers"], 1200)
        self.assertEqual(persisted_track["instagram_followers"], 800)
        self.assertEqual(persisted_track["chartmetric_instagram_sports_fit_percent"], 42.5)
        self.assertEqual(persisted_track["track_virality"], 67.5)

        remove_response = self.client.post(
            "/api/v1/my-club/favorites/toggle/",
            {"track_uuid": str(track.uuid)},
            format="json",
        )

        self.assertEqual(remove_response.status_code, 200)
        self.assertFalse(remove_response.json()["is_favorited"])
        self.assertEqual(club.track_favorites.count(), 0)


class TeamConfigEndpointTests(APITestCase):
    def test_get_team_config_by_slug(self):
        Club.objects.create(
            club_name="CF Montreal",
            slug="cfmontreal",
            team_name="CF Montréal",
            tagline="Tous ensemble, droit devant",
            colors={"primary": "#003DA6", "secondary": "#FFFFFF"},
            auth_promo={
                "image_url": "https://cdn.example.com/Montreal.png",
                "image_alt": "CF Montréal",
                "tagline": "TOUS ENSEMBLE, DROIT DEVANT",
            },
            sidenav={
                "background": "#171717",
                "border": "#404040",
                "active_background": "#262626",
                "active_border": "#FFFFFF",
                "text": "#E5E5E5",
                "muted_text": "#A3A3A3",
            },
        )

        response = self.client.get("/api/v1/teams/cfmontreal/config/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "slug": "cfmontreal",
                "country_code2": None,
                "team_name": "CF Montréal",
                "tagline": "Tous ensemble, droit devant",
                "colors": {"primary": "#003DA6", "secondary": "#FFFFFF"},
                "auth_promo": {
                    "image_url": "https://cdn.example.com/Montreal.png",
                    "image_alt": "CF Montréal",
                    "tagline": "TOUS ENSEMBLE, DROIT DEVANT",
                },
                "sidenav": {
                    "background": "#171717",
                    "border": "#404040",
                    "active_background": "#262626",
                    "active_border": "#FFFFFF",
                    "text": "#E5E5E5",
                    "muted_text": "#A3A3A3",
                },
                "instagram_url": "",
                "tiktok_url": "",
                "youtube_url": "",
            },
        )

    def test_get_team_players_by_slug(self):
        club = Club.objects.create(club_name="CF Montreal", slug="cfmontreal")
        Player.objects.create(club=club, name="Lionel Messi", nationality="AR")

        response = self.client.get("/api/v1/teams/cfmontreal/players/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["team_slug"], "cfmontreal")
        self.assertEqual(len(payload["players"]), 1)
        self.assertEqual(payload["players"][0]["name"], "Lionel Messi")
        self.assertEqual(payload["players"][0]["country_code2"], "AR")
        self.assertTrue(payload["players"][0]["id"].startswith("p_"))


class TrackPublishedLinkEndpointTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(
            username="published-links-club",
            email="published-links@example.com",
        )
        self.club = Club.objects.create(
            club_name="Published Links FC",
            slug="published-links-fc",
            user=self.user,
        )
        artist = Artist.objects.create(name="Published Artist", country="MX")
        self.track = Track.objects.create(
            artist=artist,
            isrc="MXA012600001",
            name="Published Track",
        )
        self.client.force_authenticate(self.user)

    def test_create_multiple_links_and_list_them_grouped_by_platform(self):
        endpoint = "/api/v1/my-club/published-links/"
        first = self.client.post(
            endpoint,
            {
                "track_uuid": str(self.track.uuid),
                "platform": "instagram",
                "url": "https://www.instagram.com/p/example-one/",
            },
            format="json",
        )
        second = self.client.post(
            endpoint,
            {
                "track_uuid": str(self.track.uuid),
                "platform": "instagram",
                "url": "https://www.instagram.com/reel/example-two/",
            },
            format="json",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json()["track_uuid"], str(self.track.uuid))
        self.assertEqual(self.club.published_track_links.count(), 2)

        response = self.client.get(
            endpoint,
            {"track_uuid": str(self.track.uuid)},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        self.assertEqual(len(payload["by_platform"]["instagram"]), 2)
        self.assertEqual(payload["by_platform"]["tiktok"], [])
        self.assertEqual(payload["by_platform"]["youtube"], [])
        self.assertEqual(payload["by_platform"]["youtube_shorts"], [])
        self.assertEqual(payload["by_platform"]["facebook"], [])

    def test_rejects_duplicate_url_for_same_club_and_track(self):
        endpoint = "/api/v1/my-club/published-links/"
        data = {
            "track_uuid": str(self.track.uuid),
            "platform": "youtube",
            "url": "https://www.youtube.com/watch?v=example",
        }

        self.assertEqual(self.client.post(endpoint, data, format="json").status_code, 201)
        duplicate = self.client.post(endpoint, data, format="json")

        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("url", duplicate.json())

    def test_links_are_isolated_between_clubs(self):
        link = TrackPublishedLink.objects.create(
            club=self.club,
            track=self.track,
            platform=TrackPublishedLink.Platform.TIKTOK,
            url="https://www.tiktok.com/@club/video/123",
        )
        other_user = get_user_model().objects.create(
            username="other-published-links-club",
            email="other-published-links@example.com",
        )
        other_club = Club.objects.create(
            club_name="Other Links FC",
            slug="other-links-fc",
            user=other_user,
        )
        self.client.force_authenticate(other_user)

        own_list = self.client.get(
            "/api/v1/my-club/published-links/",
            {"track_uuid": str(self.track.uuid)},
        )
        foreign_detail = self.client.get(
            f"/api/v1/my-club/published-links/{link.uuid}/"
        )
        create_for_same_track = self.client.post(
            "/api/v1/my-club/published-links/",
            {
                "track_uuid": str(self.track.uuid),
                "platform": "tiktok",
                "url": "https://www.tiktok.com/@club/video/123",
            },
            format="json",
        )

        self.assertEqual(own_list.status_code, 200)
        self.assertEqual(own_list.json()["count"], 0)
        self.assertEqual(foreign_detail.status_code, 404)
        self.assertEqual(create_for_same_track.status_code, 201)
        self.assertEqual(other_club.published_track_links.count(), 1)

    def test_patch_delete_and_input_validation(self):
        link = TrackPublishedLink.objects.create(
            club=self.club,
            track=self.track,
            platform=TrackPublishedLink.Platform.FACEBOOK,
            url="https://www.facebook.com/posts/old",
        )
        detail = f"/api/v1/my-club/published-links/{link.uuid}/"

        patched = self.client.patch(
            detail,
            {"url": "https://www.facebook.com/posts/new"},
            format="json",
        )
        invalid_platform = self.client.post(
            "/api/v1/my-club/published-links/",
            {
                "track_uuid": str(self.track.uuid),
                "platform": "spotify",
                "url": "https://open.spotify.com/track/example",
            },
            format="json",
        )
        invalid_url = self.client.post(
            "/api/v1/my-club/published-links/",
            {
                "track_uuid": str(self.track.uuid),
                "platform": "instagram",
                "url": "not-a-url",
            },
            format="json",
        )
        deleted = self.client.delete(detail)

        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["url"], "https://www.facebook.com/posts/new")
        self.assertEqual(invalid_platform.status_code, 400)
        self.assertEqual(invalid_url.status_code, 400)
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(TrackPublishedLink.objects.filter(pk=link.pk).exists())
