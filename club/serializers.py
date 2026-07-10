from rest_framework import serializers

from catalog.models import Track
from club.models import Club, Player, TrackFavorite


class TeamConfigSerializer(serializers.ModelSerializer):
    team_name = serializers.SerializerMethodField()
    tagline = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()
    auth_promo = serializers.SerializerMethodField()
    sidenav = serializers.SerializerMethodField()
    country_code2 = serializers.SerializerMethodField()

    class Meta:
        model = Club
        fields = (
            "slug",
            "country_code2",
            "team_name",
            "tagline",
            "colors",
            "auth_promo",
            "sidenav",
            "instagram_url",
            "tiktok_url",
            "youtube_url",
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

    def get_country_code2(self, obj: Club):
        if not getattr(obj, "country", None):
            return None
        return str(obj.country)


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


class TrackFavoriteSerializer(serializers.ModelSerializer):
    track_uuid = serializers.SerializerMethodField()
    track_id = serializers.SerializerMethodField()
    isrc = serializers.SerializerMethodField()
    track_name = serializers.SerializerMethodField()
    artist_name = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = TrackFavorite
        fields = ("uuid", "track_id", "track_uuid", "isrc", "track_name", "artist_name", "cover_image", "created")

    def get_track_uuid(self, obj: TrackFavorite) -> str:
        return str(obj.track.uuid)

    def get_track_id(self, obj: TrackFavorite):
        return obj.track.id

    def get_isrc(self, obj: TrackFavorite) -> str:
        return obj.track.isrc or ""

    def get_track_name(self, obj: TrackFavorite) -> str:
        return obj.track.name or ""

    def get_artist_name(self, obj: TrackFavorite) -> str:
        return getattr(obj.track.artist, "name", "") or ""

    def get_cover_image(self, obj: TrackFavorite) -> str:
        if getattr(obj.track, "cover_image", None):
            request = self.context.get("request")
            if request is not None:
                return request.build_absolute_uri(obj.track.cover_image.url)
            return obj.track.cover_image.url
        return ""
