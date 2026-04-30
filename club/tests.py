from rest_framework.test import APITestCase

from club.models import Club, Player


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
