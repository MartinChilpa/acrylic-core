from django_filters import rest_framework as rest_filters
from rest_framework import viewsets, filters
from taggit.models import Tag
from catalog.models import Track, Genre
from catalog.serializers import TrackSerializer, GenreSerializer
from common.api.pagination import StandardPagination



class TrackFilter(rest_filters.FilterSet):
    is_cover = rest_filters.BooleanFilter()
    is_remix = rest_filters.BooleanFilter()
    is_instrumental = rest_filters.BooleanFilter()
    is_explicit = rest_filters.BooleanFilter()
    released = rest_filters.DateFilter()
    genres = rest_filters.ModelMultipleChoiceFilter(queryset=Genre.objects.all(), to_field_name='code', field_name='genres')
    #tags = rest_filters.ModelMultipleChoiceFilter(queryset=Tag.objects.all(), to_field_name='name', method='filter_tags')

    class Meta:
        model = Track
        fields = ['is_cover', 'is_remix', 'is_instrumental', 'is_explicit', 'released', 'genres']

    #def filter_tags(self, queryset, name, value):
    #    return queryset.filter(tags__name__in=[tag.name for tag in value])


class TrackViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = []
    queryset = Track.objects.all()  # Adjusted from Track.active.all() to simplify the example
    lookup_field = 'uuid'
    serializer_class = TrackSerializer
    pagination_class = StandardPagination  # Ensure this is defined somewhere
    filter_backends = [rest_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TrackFilter
    search_fields = ['=uuid', '=isrc', '@name', '@artist__name', '=spotify_url']
    ordering_fields = ['name', 'created', 'updated']


class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = []
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    pagination_class = StandardPagination
    lookup_field = 'uuid'
    search_fields = ['=code', '@name']
    ordering_fields = ['name']
