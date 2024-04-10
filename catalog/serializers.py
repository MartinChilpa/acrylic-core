from rest_framework import serializers
from taggit.models import Tag
from catalog.models import Genre, Track, SyncList, SyncListTrack
from legal.serializers import MasterSplitSerializer


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name', 'slug']



class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['uuid', 'name', 'code']


class MyTrackSerializer(serializers.ModelSerializer):
    artist = serializers.SlugRelatedField(slug_field='uuid', read_only=True)
    tags = TagSerializer(many=True)
    genres = GenreSerializer(many=True)
    additional_main_artists = serializers.SlugRelatedField(slug_field='uuid', read_only=True, many=True)
    featured_artists = serializers.SlugRelatedField(slug_field='uuid', read_only=True, many=True)

    class Meta:
        model = Track
        fields = '__all__'  # Lists all fields from the Track model. Adjust as needed.
        extra_kwargs = {
            'file_mp3': {'required': False},
            'file_wav': {'required': False},
            'snippet': {'required': False},
        }


class TrackSerializer(serializers.ModelSerializer):
    master_splits = MasterSplitSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True)
    genres = GenreSerializer(many=True)
    artist = serializers.SlugRelatedField(slug_field='uuid', read_only=True)

    class Meta:
        model = Track
        fields = [
            'uuid', 'isrc', 'artist', 'name', 'duration', 'released', 'is_cover',
            'is_remix', 'is_instrumental', 'is_explicit', 'record_type', 'bpm',
            'language', 'lyrics', 'snippet', 'genres', 'additional_main_artists',
            'featured_artists', 'tags', 'master_splits'
        ]

    def get_genre_names(self, obj):
        return [genre.name for genre in obj.genres.all()]


class SyncListTrackSerializer(serializers.ModelSerializer):
    track = TrackSerializer(read_only=True)
    
    class Meta:
        model = SyncListTrack
        fields = ['track', 'order']


class SyncListSerializer(serializers.ModelSerializer):
    tracks = SyncListTrackSerializer(source='synclisttrack_set', many=True, read_only=True)
    artist = serializers.SlugRelatedField(slug_field='uuid', read_only=True)

    class Meta:
        model = SyncList
        fields = ['uuid', 'artist', 'name', 'description', 'order', 'pinned', 'tracks']

    def create(self, validated_data):
        # Ensure the SyncList is associated with the current artist.
        validated_data['artist'] = self.context['request'].user.artist
        return super().create(validated_data)