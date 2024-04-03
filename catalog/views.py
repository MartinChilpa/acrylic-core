from django_filters import rest_framework as filters
from rest_framework import viewsets
from taggit.models import Tag
from catalog.models import Track, Genre
from catalog.serializers import TrackSerializer
from common.api.pagination import StandardPagination



class TrackFilter(filters.FilterSet):
    is_cover = filters.BooleanFilter()
    is_remix = filters.BooleanFilter()
    is_instrumental = filters.BooleanFilter()
    is_explicit = filters.BooleanFilter()
    released = filters.DateFilter()
    genres = filters.ModelMultipleChoiceFilter(queryset=Genre.objects.all(), to_field_name='id', field_name='genres')
    #tags = filters.ModelMultipleChoiceFilter(queryset=Tag.objects.all(), to_field_name='name', method='filter_tags')

    class Meta:
        model = Track
        fields = ['is_cover', 'is_remix', 'is_instrumental', 'is_explicit', 'released', 'genres']

    #def filter_tags(self, queryset, name, value):
    #    return queryset.filter(tags__name__in=[tag.name for tag in value])


class TrackViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Track.objects.all()  # Adjusted from Track.active.all() to simplify the example
    lookup_field = 'uuid'
    serializer_class = TrackSerializer
    pagination_class = StandardPagination  # Ensure this is defined somewhere
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = TrackFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        isrc = self.request.query_params.get('isrc', None)
        spotify_url = self.request.query_params.get('spotify_url', None)
        name = self.request.query_params.get('name', None)
        artist_name = self.request.query_params.get('artist_name', None)

        if isrc:
            queryset = queryset.filter(isrc=isrc)
        if spotify_url:
            queryset = queryset.filter(artist__spotify_url=spotify_url)
        if name:
            queryset = queryset.filter(name__icontains=name)
        if artist_name:
            queryset = queryset.filter(artist__name__icontains=artist_name)

        return queryset