from rest_framework import serializers
from django.core.mail import EmailMessage
from django.conf import settings
from django.db import IntegrityError
import logging

from license.models import License
from license.tasks import build_whitelist_email
from catalog.models import Track

logger = logging.getLogger(__name__)


class LicenseSerializer(serializers.ModelSerializer):
    track = serializers.CharField(write_only=True)
    extended_commercial_use = serializers.BooleanField(write_only=True, required=False, default=False)
    track_uuid = serializers.CharField(source='track.uuid', read_only=True)
    track_id = serializers.IntegerField(source='track.id', read_only=True)
    isrc = serializers.CharField(source='track.isrc', read_only=True)
    track_name = serializers.CharField(source='track.name', read_only=True)
    artist_name = serializers.SerializerMethodField()
    instagram_url = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = License
        fields = [
            'uuid', 'track', 'extended_commercial_use', 'track_uuid', 'track_id', 'isrc', 'track_name',
            'artist_name', 'instagram_url', 'cover_image', 'status', 'created', 'updated'
        ]
        read_only_fields = ['uuid', 'status', 'created', 'updated']

    def get_artist_name(self, obj):
        return obj.track.artist.name if obj.track.artist else ''

    def get_instagram_url(self, obj):
        artist = obj.track.artist
        return artist.instagram_url if artist else None

    def get_cover_image(self, obj):
        if not obj.track.cover_image:
            return None
        url = str(obj.track.cover_image)
        if url.startswith('http'):
            return url
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.track.cover_image.url)
        return url

    def validate(self, data):
        request = self.context.get('request')
        if not request or not request.user or not hasattr(request.user, 'club'):
            raise serializers.ValidationError("User must be a club to create a license.")

        club = request.user.club
        track_identifier = self.initial_data.get('track')
        extended_commercial_use_flag = self.initial_data.get('extended_commercial_use', False)
        if isinstance(extended_commercial_use_flag, str):
            extended_commercial_use_flag = extended_commercial_use_flag.lower() in ('true', '1', 'yes')

        logger.info(
            f"[License] validate() called: track_identifier={track_identifier}, "
            f"extended_commercial_use={extended_commercial_use_flag}"
        )

        # Validate track exists — try UUID first, then ISRC, then spotify_id
        track = None
        if track_identifier:
            try:
                track = Track.objects.get(uuid=track_identifier)
                logger.info(f"[License] Found track by UUID: {track.uuid}")
            except Track.DoesNotExist:
                try:
                    track = Track.objects.get(isrc=track_identifier)
                    logger.info(f"[License] Found track by ISRC: {track.isrc}")
                except Track.DoesNotExist:
                    try:
                        track = Track.objects.get(spotify_id=track_identifier)
                        logger.info(f"[License] Found track by spotify_id: {track.spotify_id}")
                    except Track.DoesNotExist:
                        logger.warning(f"[License] Track not found: {track_identifier}")

        if not track:
            raise serializers.ValidationError({"track": f"Track not found."})

        # Validate track has isrc and distributor
        if not track.isrc:
            logger.error(f"[License] Track {track.uuid} has no ISRC")
            raise serializers.ValidationError({"track": "Track must have an ISRC."})
        if not track.distributor:
            logger.error(f"[License] Track {track.uuid} has no distributor")
            raise serializers.ValidationError({"track": "Track must have a distributor."})

        # Validate distributor has whitelist email only when we need to send the email.
        if extended_commercial_use_flag:
            distributor = track.distributor
            if not distributor:
                logger.error(f"[License] Track {track.uuid} has no distributor")
                raise serializers.ValidationError({"track": "Track must have a distributor for extended commercial use."})
            if not distributor.whitelist_email:
                logger.error(f"[License] Distributor {distributor.id} has no whitelist_email")
                raise serializers.ValidationError({"track": "Distributor not configured for whitelisting."})

            # Validate club has required social URLs for email sending
            if not (club.instagram_url and club.tiktok_url and club.youtube_url):
                logger.error(f"[License] Club {club.id} missing required social URLs")
                raise serializers.ValidationError({"detail": "Club must configure Instagram, TikTok, and YouTube URLs."})

        # Check for duplicate license
        existing = License.objects.filter(club=club, track=track).exists()
        if existing:
            logger.warning(f"[License] Duplicate license for club={club.id}, track={track.uuid}")
            raise serializers.ValidationError({"detail": "License already exists for this track."})

        data['club'] = club
        data['track'] = track
        data['extended_commercial_use'] = extended_commercial_use_flag
        return data

    def create(self, validated_data):
        send_whitelist_email = validated_data.pop('extended_commercial_use', False)
        try:
            license_obj = License.objects.create(
                club=validated_data['club'],
                track=validated_data['track'],
                status=License.STATUS_PENDING,
            )
        except IntegrityError:
            raise serializers.ValidationError({"detail": "License already exists for this track."})

        if send_whitelist_email:
            try:
                subject, from_email, to_email, body, reply_to = build_whitelist_email(license_obj)
                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=from_email,
                    to=[to_email],
                    headers={'Reply-To': reply_to},
                )
                email.send()
                license_obj.email_sent = True
            except Exception as e:
                logger.error(f"Failed to send whitelist email for License {license_obj.uuid}: {str(e)}")
                license_obj.email_error = str(e)
        else:
            license_obj.email_sent = False

        license_obj.save()
        return license_obj
