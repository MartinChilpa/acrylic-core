from django.db.models import Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.api.pagination import StandardPagination
from catalog.serializers import TrackSerializer
from artist.api.serializers import ArtistSerializer
from artist.models import Artist


class ArtistViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Artist.active.all()
    lookup_field = 'uuid'
    serializer_class = ArtistSerializer
    pagination_class = StandardPagination

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
    