from rest_framework import serializers
from taggit.models import Tag
from catalog.models import Distributor, Genre, Price, TierPrice, Track, SyncList, SyncListTrack
from buyer.serializers import TierSerializer

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


class TierPriceSerializer(serializers.ModelSerializer):
    tier = TierSerializer(many=False, read_only=True)

    class Meta:
        model = TierPrice
        fields = ['tier', 'single_use_price', 'subscription_price']


class PriceSerializer(serializers.ModelSerializer):
    tier_prices = TierPriceSerializer(many=True, read_only=True)
    min_price = serializers.SerializerMethodField()
    max_price = serializers.SerializerMethodField()

    class Meta:
        model = Price
        fields = ['uuid', 'name', 'description', 'max_artist_tracks', 'tier_prices', 'default', 'active', 'order', 'min_price', 'max_price']
        queryset = Price.objects.prefetch_related('tier_prices', 'tier_prices__tier')    

    def get_min_price(self, obj):
        lowest_price = obj.tier_prices.order_by('subscription_price').first()
        return lowest_price.subscription_price
    
    def get_max_price(self, obj):
        highest_price = obj.tier_prices.order_by('-single_use_price').first()
        return highest_price.single_use_price


class MyTrackSerializer(serializers.ModelSerializer):
    artist = serializers.SlugRelatedField(slug_field='uuid', read_only=True)
    distributor = serializers.SlugRelatedField(slug_field='uuid', queryset=Distributor.objects.all(), required=False)
    tags = TagSerializer(many=True, required=False)
    genres = GenreSerializer(many=True, required=False)
    additional_main_artists = serializers.SlugRelatedField(slug_field='uuid', read_only=True, many=True)
    featured_artists = serializers.SlugRelatedField(slug_field='uuid', read_only=True, many=True)
    price = serializers.SlugRelatedField(slug_field='uuid', queryset=Price.objects.all(), many=False)

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
