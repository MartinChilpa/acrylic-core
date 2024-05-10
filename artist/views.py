from django.conf import settings
from django.db.models import Count
from django.http import Http404
from django_filters import rest_framework as rest_filters
from rest_framework import filters, viewsets, mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_registration.api.views.register import RegisterView
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from taggit.models import Tag
from artist.permissions import IsArtistOwner
from common.api.pagination import StandardPagination
from catalog.serializers import TrackSerializer
from artist.serializers import ArtistSerializer, RegisterArtistSerializer
from artist.models import Artist
from catalog.models import Track


class ArtistFilter(rest_filters.FilterSet):
    #country = rest_filters.ChoiceFilter(field_name='country', lookup_expr='exact')
    tags = rest_filters.ModelMultipleChoiceFilter(queryset=Tag.objects.all(), to_field_name='name', method='tags_filter')


    def tags_filter(self, queryset, name, value):
        if value:
            return queryset.filter(tags__in=value) 
        return queryset

    class Meta:
        model = Artist
        fields = {
            'slug': ['exact'],
            'tags': ['exact'],
        }

#@extend_schema(
#    parameters=[
#        # Documenting search fields
#        OpenApiParameter(name='search', description='Search artists by name, bio, Spotify URL or tags', required=False, type=str),
#        # Documenting ordering fields
#        OpenApiParameter(name='ordering', description='Order by name, created, or updated', required=False, type=str),
#    ],
#)    
class ArtistViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = []
    authentication_classes = []
    lookup_field = 'uuid'
    queryset = Artist.active.all()
    serializer_class = ArtistSerializer
    pagination_class = StandardPagination
    filter_backends = [rest_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ArtistFilter
    search_fields = ['name', 'slug', 'bio', '=spotify_url', 'tags__name']
    ordering_fields = ['name', 'created', 'updated']
    
    @action(detail=True, methods=['get'])
    def tracks(self, request, uuid=None):
        """
        Returns a list of tracks for the artist identified by the uuid.
        """
        artist = self.get_object()  # Retrieves the Artist instance based on the provided UUID
        tracks = artist.tracks.all()  # Adjust the filter based on your relationship field
        page = self.paginate_queryset(tracks)
        if page is not None:
            serializer = TrackSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = TrackSerializer(tracks, many=True, context={'request': request})
        return Response(serializer.data)


class MyArtistViewSet(viewsets.GenericViewSet):
    serializer_class = ArtistSerializer
    queryset = Artist.objects.none()
    permission_classes = [permissions.IsAuthenticated, IsArtistOwner]

    def get_object(self):
        instance = getattr(self.request.user, 'artist', None)
        if not instance:
            raise Http404('No Artist profile instance found.')
        return instance

    @action(detail=False, methods=['get'])
    def profile(self, request):
        """
        Retrieve the singleton instance.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ArtistRegisterView(RegisterView):
    serializer_class = RegisterArtistSerializer