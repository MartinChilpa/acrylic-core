from django.db import IntegrityError, transaction
from rest_framework import serializers

from catalog.models import Track
from club.models import Club, Player, TrackFavorite, TrackPublishedLink


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
    track = serializers.SerializerMethodField()
    track_uuid = serializers.SerializerMethodField()
    track_id = serializers.SerializerMethodField()
    isrc = serializers.SerializerMethodField()
    track_name = serializers.SerializerMethodField()
    artist_name = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = TrackFavorite
        fields = (
            "uuid",
            "track_id",
            "track_uuid",
            "isrc",
            "track_name",
            "artist_name",
            "cover_image",
            "track",
            "created",
        )

    def _file_url(self, value) -> str:
        if not value:
            return ""
        url = value.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request is not None else url

    def get_track(self, obj: TrackFavorite) -> dict:
        track = obj.track
        artist = track.artist
        price = track.price
        price_temp = price.price_temp if price else None

        return {
            "uuid": str(track.uuid),
            "track_id": track.id,
            "track_uuid": str(track.uuid),
            "isrc": track.isrc or "",
            "track_name": track.name or "",
            "name": track.name or "",
            "artist_name": artist.name or "",
            "artist_canonical": artist.name or "",
            "artist_country_code2": str(artist.country) if artist.country else None,
            "cover_image": self._file_url(track.cover_image),
            "file_wav": self._file_url(track.file_wav),
            "file_mp3": self._file_url(track.file_mp3),
            "waveform": self._file_url(track.waveform),
            "waveform_url": self._file_url(track.waveform),
            "duration": int(track.duration / 1000) if track.duration else None,
            "release_year": track.released.year if track.released else None,
            "track_virality": track.virality,
            "virality": track.virality,
            "extended_commercial_use": track.extended_commercial_use,
            "price_id": track.price_id,
            "price_uuid": str(price.uuid) if price else None,
            "price_temp": price_temp,
            "price": price_temp,
            "price_description": price.description if price else None,
            "descripcion": price.description if price else None,
            "youtube_restriction": track.youtube_restriction,
            "archival": track.archival,
            "spotify_followers": artist.spotify_followers,
            "instagram_followers": artist.instagram_followers,
            "youtube_followers": artist.youtube_followers,
            "tiktok_followers": artist.tiktok_followers,
            "chartmetric_instagram_demographics": artist.chartmetric_instagram_demographics,
            "chartmetric_instagram_top_cities": artist.chartmetric_instagram_top_cities,
            "chartmetric_instagram_top_countries": artist.chartmetric_instagram_top_countries,
            "chartmetric_instagram_sports_fit_percent": artist.chartmetric_instagram_sports_fit_percent,
        }

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


class TrackPublishedLinkSerializer(serializers.ModelSerializer):
    track_uuid = serializers.SlugRelatedField(
        source="track",
        slug_field="uuid",
        queryset=Track.objects.all(),
    )
    track_id = serializers.IntegerField(source="track.id", read_only=True)
    track_name = serializers.CharField(source="track.name", read_only=True)
    platform_display = serializers.CharField(source="get_platform_display", read_only=True)

    class Meta:
        model = TrackPublishedLink
        fields = (
            "uuid",
            "track_uuid",
            "track_id",
            "track_name",
            "platform",
            "platform_display",
            "url",
            "created",
            "updated",
        )
        read_only_fields = (
            "uuid",
            "track_id",
            "track_name",
            "platform_display",
            "created",
            "updated",
        )

    def validate(self, attrs):
        request = self.context.get("request")
        club = getattr(getattr(request, "user", None), "club", None)
        if club is None:
            raise serializers.ValidationError({"detail": "No club found for this user."})

        track = attrs.get("track") or getattr(self.instance, "track", None)
        url = attrs.get("url") or getattr(self.instance, "url", None)
        if track is not None and url:
            duplicate = TrackPublishedLink.objects.filter(
                club=club,
                track=track,
                url=url,
            )
            if self.instance is not None:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError(
                    {"url": "This published link already exists for this track."}
                )

        attrs["club"] = club
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {"url": "This published link already exists for this track."}
            )

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {"url": "This published link already exists for this track."}
            )
