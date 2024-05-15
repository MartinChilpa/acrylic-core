from rest_framework import serializers


class TrackPreviewSerializer(serializers.Serializer):
    isrc = serializers.CharField(max_length=12)
    name = serializers.CharField(max_length=250)
    artist = serializers.CharField(max_length=250)
    spotify_id = serializers.CharField(max_length=50)
    image = serializers.URLField(required=False, allow_blank=True)
    spotify_url = serializers.URLField()
    duration = serializers.IntegerField()
