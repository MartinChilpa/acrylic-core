from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from artist.models import Artist
from catalog.models import Track
from club.models import Club, Player


class TrackFavoriteEndpointTests(APITestCase):
    def test_toggle_and_list_track_favorites_for_club(self):
        user = get_user_model().objects.create(username="club-admin", email="club@example.com")
        club = Club.objects.create(club_name="CF Montreal", slug="cfmontreal", user=user)
        artist = Artist.objects.create(name="Test Artist", country="ES")                                    
        track = Track.objects.create(artist=artist, isrc="USE100000001", name="Saved Track")

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
