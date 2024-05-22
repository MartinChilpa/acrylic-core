from rest_framework import serializers
from taggit.models import Tag
from catalog.models import Distributor, Genre, Price, Track, SyncList, SyncListTrack


class DistributorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distributor
        fields = ['uuid', 'name']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name', 'slug']


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['uuid', 'name', 'code']


class PriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = ['uuid', 'name', 'description', 'single_use_price', 'max_artist_tracks', 'default', 'active', 'order']


class MyTrackSerializer(serializers.ModelSerializer):
    artist = serializers.SlugRelatedField(slug_field='uuid', read_only=True)
    distributor = serializers.SlugRelatedField(slug_field='uuid', queryset=Distributor.objects.all(), required=False)
    tags = TagSerializer(many=True, required=False)
    genres = GenreSerializer(many=True, required=False)
    additional_main_artists = serializers.SlugRelatedField(slug_field='uuid', read_only=True, many=True)
    featured_artists = serializers.SlugRelatedField(slug_field='uuid', read_only=True, many=True)
    price = serializers.SlugRelatedField(slug_field='uuid', many=False)

    class Meta:
        model = Track
        # fields = '__all__'  # Lists all fields from the Track model. Adjust as needed.
        exclude = ['id']
        extra_kwargs = {
            'file_mp3': {'required': False},
            'file_wav': {'required': False},
            'snippet': {'required': False},
            'cover_image': {'required': False},
        }


class MyTrackReadSerializer(MyTrackSerializer):
    price = PriceSerializer(many=False, read_only=True)


class TrackSummarySerializer(serializers.ModelSerializer):
    artist = serializers.SlugRelatedField(slug_field='name', read_only=True)
    class Meta:
        model = Track
        fields = [
            'uuid', 'isrc', 'artist', 'name', 'duration', 'released', 'bpm',
            'language', 'lyrics', 'snippet'
        ]


class TrackSerializer(serializers.ModelSerializer):
    artist = serializers.SlugRelatedField(slug_field='uuid', read_only=True)
    distributor = serializers.SlugRelatedField(slug_field='uuid', read_only=True)
    tags = TagSerializer(many=True)
    genres = GenreSerializer(many=True)
    price = serializers.SlugRelatedField(slug_field='uuid', read_only=True)

    class Meta:
        model = Track
        fields = [
            'uuid', 'isrc', 'artist', 'name', 'duration', 'released', 'is_cover',
            'is_remix', 'is_instrumental', 'is_explicit', 'bpm',
            'language', 'lyrics', 'distributor', 'snippet', 'genres', 
            'additional_main_artists', 'featured_artists', 'tags',
            'price',
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

    genres = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = SyncList
        fields = ['uuid', 'artist', 'name', 'cover_image', 'background_image', 'description', 'order', 'pinned', 'tracks', 'genres', 'tags']

    def create(self, validated_data):
        # Ensure the SyncList is associated with the current artist.
        validated_data['artist'] = self.context['request'].user.artist
        return super().create(validated_data)

    def get_genres(self, obj):
        # Assuming `get_tags()` returns a queryset of Tag instances
        tags = obj.get_genres()
        return GenreSerializer(tags, many=True, context=self.context).data
    
    def get_tags(self, obj):
        # Assuming `get_tags()` returns a queryset of Tag instances
        tags = obj.get_tags()
        return TagSerializer(tags, many=True, context=self.context).data
