from rest_framework import serializers

from club.models import Club, Player


class TeamConfigSerializer(serializers.ModelSerializer):
    team_name = serializers.SerializerMethodField()
    tagline = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()
    auth_promo = serializers.SerializerMethodField()
    sidenav = serializers.SerializerMethodField()

    class Meta:
        model = Club
        fields = (
            "slug",
            "team_name",
            "tagline",
            "colors",
            "auth_promo",
            "sidenav",
        )

    def get_team_name(self, obj: Club) -> str:
        return (obj.team_name or obj.club_name or "").strip()

    def get_tagline(self, obj: Club) -> str:
        return (obj.tagline or "").strip()

    def get_colors(self, obj: Club) -> dict:
        return obj.colors or {}

    def get_auth_promo(self, obj: Club) -> dict:
        return obj.auth_promo or {}

    def get_sidenav(self, obj: Club) -> dict:
        return obj.sidenav or {}


class TeamPlayerSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    country_code2 = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = ("id", "name", "country_code2")

    def get_id(self, obj: Player) -> str:
        return f"p_{obj.id}"

    def get_country_code2(self, obj: Player):
        if not obj.nationality:
            return None
        return str(obj.nationality)
