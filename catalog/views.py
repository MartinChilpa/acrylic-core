from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as rest_filters
from rest_framework import viewsets, filters, permissions, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, inline_serializer
from taggit.models import Tag
from common.api.pagination import StandardPagination
from artist.permissions import IsArtistOwner, IsTrackArtistOwner
from catalog.models import Distributor, Track, Genre, Price, SyncList, SyncListTrack
from catalog.serializers import (
    DistributorSerializer, TrackSerializer, MyTrackSerializer, MyTrackReadSerializer, 
    GenreSerializer, SyncListSerializer, SyncListTrackSerializer, PriceSerializer, MyPriceSerializer
)


class TrackFilter(rest_filters.FilterSet):
    is_cover = rest_filters.BooleanFilter()
    is_remix = rest_filters.BooleanFilter()
    is_instrumental = rest_filters.BooleanFilter()
    is_explicit = rest_filters.BooleanFilter()
    released = rest_filters.DateFilter()
    genres = rest_filters.ModelMultipleChoiceFilter(queryset=Genre.objects.all(), to_field_name='code', field_name='genres')
    tags = rest_filters.ModelMultipleChoiceFilter(queryset=Tag.objects.all(), to_field_name='name', method='tags_filter')

    def tags_filter(self, queryset, name, value):
        if value:
            return queryset.filter(tags__in=value) 
        return queryset

    class Meta:
        model = Track
        fields = ['is_cover', 'is_remix', 'is_instrumental', 'is_explicit', 'released', 'genres']

    #def filter_tags(self, queryset, name, value):
    #    return queryset.filter(tags__name__in=[tag.name for tag in value])


@extend_schema(
    parameters=[
        # Documenting search fields
        OpenApiParameter(name='search', description='Search tracks by UUID, ISRC, name, or artist name', required=False, type=str),
        # Documenting ordering fields
        OpenApiParameter(name='ordering', description='Order by name, created, or updated', required=False, type=str),
    ],
)
class TrackViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = []
    authentication_classes = []
    queryset = Track.objects.select_related('artist').prefetch_related('genres', 'tags', 'additional_main_artists', 'featured_artists')  # Adjusted from Track.active.all() to simplify the example
    lookup_field = 'uuid'
    serializer_class = TrackSerializer
    pagination_class = StandardPagination
    filter_backends = [rest_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TrackFilter
    search_fields = ['=uuid', '=isrc', 'name', 'artist__name']
    ordering_fields = ['name', 'created', 'updated']

    
class MyTrackViewSet(viewsets.ModelViewSet):
    serializer_class = MyTrackSerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticated, IsArtistOwner]
    queryset = Track.objects.none()  # Default queryset is none, will be dynamically set in get_queryset
    lookup_field = 'uuid'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'isrc']
    ordering_fields = ['released', 'name', 'created', 'updated']

    def get_queryset(self):
        user_artist = self.request.user.artist
        return Track.objects.filter(artist=user_artist).select_related('distributor', 'artist').prefetch_related('genres', 'tags', 'additional_main_artists', 'featured_artists')

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return MyTrackReadSerializer
        return MyTrackSerializer

    def perform_create(self, serializer):
        """
        Automatically set the artist to the logged-in user's artist
        when creating a new track.
        """
        serializer.save(artist=self.request.user.artist)


@extend_schema(
    parameters=[
        OpenApiParameter(name='code', description='Search by code', required=False, type=str),
        OpenApiParameter(name='name', description='Search by name', required=False, type=str),
    ],
)
class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = []
    authentication_classes = []
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    pagination_class = StandardPagination
    lookup_field = 'uuid'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['=code', 'name']
    ordering_fields = ['name']


class PriceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = []
    authentication_classes = []
    queryset = Price.objects.all()
    serializer_class = PriceSerializer
    pagination_class = StandardPagination
    lookup_field = 'uuid'


class MyPriceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Price.objects.all()
    serializer_class = MyPriceSerializer
    pagination_class = StandardPagination
    lookup_field = 'uuid'


@extend_schema(
    parameters=[
        OpenApiParameter(name='name', description='Search by name', required=False, type=str),
    ],
)
class DistributorViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = []
    authentication_classes = []
    queryset = Distributor.objects.all()
    serializer_class = DistributorSerializer
    pagination_class = StandardPagination
    lookup_field = 'uuid'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']


class SyncListViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = []
    authentication_classes = []
    queryset = SyncList.objects.none()
    serializer_class = SyncListSerializer
    pagination_class = StandardPagination
    lookup_field = 'uuid'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['order']

    def get_queryset(self):
        sync_list_tracks_prefetch = Prefetch('synclisttrack_set', queryset=SyncListTrack.objects.select_related('track'))
        return SyncList.objects.select_related('artist').prefetch_related(sync_list_tracks_prefetch)


class MySyncListViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsArtistOwner]
    serializer_class = SyncListSerializer
    queryset = SyncList.objects.none()
    lookup_field = 'uuid'
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['order']

    def get_queryset(self):
        sync_list_tracks_prefetch = Prefetch('synclisttrack_set', queryset=SyncListTrack.objects.select_related('track'))
        return self.request.user.artist.synclists.prefetch_related(sync_list_tracks_prefetch)

    def get_synclist_object(self, uuid):
        qs = self.get_queryset()
        try:
            return qs.get(uuid=uuid)
        except SyncList.DoesNotExist:
            raise SyncList.DoesNotExist

    def perform_create(self, serializer):
        """
        Automatically set the artist to the logged-in user's artist
        when creating a new track.
        """
        serializer.save(artist=self.request.user.artist)

    @extend_schema(
        request=inline_serializer(
            name='AddTracksSerializer',
            fields={
                'tracks': serializers.ListField(
                    child=inline_serializer(
                        name='TrackData',
                        fields={
                            'track_uuid': serializers.UUIDField(format='hex_verbose'),
                            'order': serializers.IntegerField(required=False)
                        }
                    )
                )
            }
        ),
        responses={201: None},
        methods=['POST'],
        description="Add multiple tracks to a SyncList.",
        examples=[
            OpenApiExample(
                name="Example payload",
                description="This is an example payload for adding tracks to a SyncList.",
                value=[
                    {"track_uuid": "uuid-of-track-1", "order": 1},
                    {"track_uuid": "uuid-of-track-2", "order": 2}
                ],
                request_only=True,  # This example only applies to the request
            ),
        ]
    )
    @action(detail=True, methods=['post'], url_path='add-tracks')
    def add_tracks(self, request, uuid=None):
        try:
            synclist = self.get_synclist_object(uuid)
        except SyncList.DoesNotExist:
            return Response({'detail': 'SyncList not found'}, status=status.HTTP_404_NOT_FOUND)

        tracks_data = request.data.get('tracks', [])

        if not isinstance(tracks_data, list) or not tracks_data:
            return Response({"detail": "Tracks data must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)

        for track_data in tracks_data:
            track_uuid = track_data.get('track_uuid')
            order = track_data.get('order', 0)
            track = get_object_or_404(Track, uuid=track_uuid)
            
            # Validate if the track belongs to the artist, if required
            # if track.artist != self.request.user.artist:
            #     continue
            SyncListTrack.objects.update_or_create(
                synclist=synclist,
                track=track,
                defaults={'order': order}
            )

        return Response({"detail": "Tracks added/updated successfully."}, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=inline_serializer(
            name='RemoveTracksSerializer',
            fields={
                'tracks': serializers.ListField(
                    child=inline_serializer(
                        name='RemoveTrackData',
                        fields={
                            'track_uuid': serializers.UUIDField(format='hex_verbose'),
                        }
                    )
                )
            }
        ),
        responses={204: None},
        methods=['POST'],
        description="Remove a track or multiple tracks from a SyncList.",
        examples=[
            OpenApiExample(
                name="Example payload for multiple tracks",
                description="This is an example payload for removing tracks from a SyncList.",
                 value=[
                    {"track_uuid": "uuid-of-track-1"},
                    {"track_uuid": "uuid-of-track-2"},
                ],
                request_only=True,
            ),
        ]
    )
    @action(detail=True, methods=['post'], url_path='remove-tracks')
    def remove_tracks(self, request, uuid=None):
        try:
            synclist = self.get_synclist_object(uuid)
        except SyncList.DoesNotExist:
            return Response({'detail': 'SyncList not found'}, status=status.HTTP_404_NOT_FOUND)
        
        tracks_data = request.data.get('tracks', [])

        if not isinstance(tracks_data, list) or not tracks_data:
            return Response({"detail": "Tracks data must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)

        count = 0
        for track_data in tracks_data:
            track_uuid = track_data.get('track_uuid')
            count += SyncListTrack.objects.filter(synclist=synclist, track__uuid=track_uuid).delete()[0]
               
        message = f"{count} tracks removed successfully." if count else "No tracks found to remove."
        return Response({"detail": message}, status=status.HTTP_204_NO_CONTENT)
