from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings
import logging

from license.models import License
from license.tasks import build_whitelist_email
from catalog.models import Track

logger = logging.getLogger(__name__)


class LicenseSerializer(serializers.ModelSerializer):
    track_uuid = serializers.CharField(source='track.uuid', read_only=True)
    track_id = serializers.IntegerField(source='track.id', read_only=True)
    isrc = serializers.CharField(source='track.isrc', read_only=True)
    track_name = serializers.CharField(source='track.name', read_only=True)
    artist_name = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = License
        fields = [
            'uuid', 'track', 'track_uuid', 'track_id', 'isrc', 'track_name',
            'artist_name', 'cover_image', 'extended_commercial_use', 'total_price',
            'status', 'created', 'updated'
        ]
        read_only_fields = ['uuid', 'status', 'created', 'updated']

    def get_artist_name(self, obj):
        return obj.track.artist.name if obj.track.artist else ''

    def get_cover_image(self, obj):
        if not obj.track.cover_image:
            return None
        # Return absolute URL for S3 or local files
        url = str(obj.track.cover_image)
        if url.startswith('http'):
            return url
        # Build absolute URL for relative paths
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.track.cover_image.url)
        return url

    def get_total_price(self, obj):
        # Calculate price based on tier and extended_commercial_use
        if obj.tier and obj.tier.code == 'artistpromo':
            # artistpromo: $0 base + $300 if extended_commercial_use
            base = 0
            addon = 300 if obj.extended_commercial_use else 0
            return f"{base + addon}.00"
        elif obj.tier and obj.tier.code == 'bid2clear':
            # bid2clear: $1500 base + $300 if extended_commercial_use
            base = 1500
            addon = 300 if obj.extended_commercial_use else 0
            return f"{base + addon}.00"
        # Default to 0
        return "0.00"

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user or not hasattr(request.user, 'club'):
            raise serializers.ValidationError("User must be a club to create a license.")

        club = request.user.club
        track_uuid = self.initial_data.get('track')
        selected_platforms = self.initial_data.get('selected_platforms', [])
        extended_commercial_use = self.initial_data.get('extended_commercial_use', False)

        # Validate track exists
        try:
            track = Track.objects.get(uuid=track_uuid)
        except Track.DoesNotExist:
            raise serializers.ValidationError({"track": "Track not found."})

        # Validate selected_platforms is not empty
        if not selected_platforms or not isinstance(selected_platforms, list):
            raise serializers.ValidationError({"selected_platforms": "At least one platform must be selected."})

        # Validate each selected platform has a URL on the club
        platform_urls = {
            'instagram': club.instagram_url,
            'tiktok': club.tiktok_url,
            'youtube': club.youtube_url,
            'other': club.other_url,
        }
        for platform in selected_platforms:
            if platform not in platform_urls or not platform_urls[platform]:
                raise serializers.ValidationError(
                    {"selected_platforms": f"Platform '{platform}' is not configured on this club."}
                )

        # Validate track has isrc and distributor
        if not track.isrc:
            raise serializers.ValidationError({"track": "Track must have an ISRC."})
        if not track.distributor:
            raise serializers.ValidationError({"track": "Track must have a distributor."})

        # Validate distributor is set up for whitelisting
        distributor = track.distributor
        if not distributor.whitelist_send or not distributor.whitelist_email:
            raise serializers.ValidationError(
                {"track": "Distributor is not configured to send whitelist emails."}
            )

        # Check for duplicate license
        existing = License.objects.filter(club=club, track=track).exists()
        if existing:
            raise serializers.ValidationError(
                "A license request already exists for this track."
            )

        # Create the license record
        license_obj = License.objects.create(
            club=club,
            track=track,
            tier=club.user.buyer.tier if hasattr(club.user, 'buyer') else None,
            status=License.STATUS_PENDING,
            extended_commercial_use=extended_commercial_use,
            selected_platforms=selected_platforms,
        )

        # Send whitelist email synchronously
        try:
            subject, from_email, to_email, body, reply_to = build_whitelist_email(license_obj)
            send_mail(
                subject=subject,
                message=body,
                from_email=from_email,
                recipient_list=[to_email],
                headers={'Reply-To': reply_to},
            )
            license_obj.email_sent = True
        except Exception as e:
            logger.error(f"Failed to send whitelist email for License {license_obj.uuid}: {str(e)}")
            license_obj.email_error = str(e)

        license_obj.save()
        return license_obj
