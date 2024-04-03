from rest_framework import serializers
from catalog.models import Genre, Track, MasterSplit
from taggit.models import Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name', 'slug']



class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['uuid', 'name', 'code']



class MasterSplitSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterSplit
        fields = ['uuid', 'owner_name', 'owner_email', 'percent', 'validated']



class TrackSerializer(serializers.ModelSerializer):
    master_splits = MasterSplitSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True)
    genres = GenreSerializer(many=True)

    class Meta:
        model = Track
        fields = [
            'uuid', 'isrc', 'artist', 'name', 'duration', 'released', 'is_cover',
            'is_remix', 'is_instrumental', 'is_explicit', 'record_type', 'bpm',
            'language', 'lyrics', 'snippet', 'file_wav', 'file_mp3', 'genres',
            'additional_main_artists', 'featured_artists', 'tags', 'master_splits'
        ]

    def get_genre_names(self, obj):
        return [genre.name for genre in obj.genres.all()]
