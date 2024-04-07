from django.conf import settings
from django.db.models import Count
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_registration.api.views.register import RegisterView

from common.api.pagination import StandardPagination
from catalog.serializers import TrackSerializer
from artist.serializers import ArtistSerializer, RegisterArtistSerializer
from artist.models import Artist
from catalog.models import Track


class MyTrackViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    """
    A simple ViewSet for viewing items owned by the logged-in user.
    """
    serializer_class = TrackSerializer
    permission_classes = [IsAuthenticated]
    queryset = Track.objects.none()
    lookup_field = 'uuid'

    def get_queryset(self):
        """
        This view should return a list of all the items
        for the currently authenticated user.
        """
        user = self.request.user
        return user.artist.tracks.all()
    


class ArtistViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Artist.active.all()
    lookup_field = 'uuid'
    serializer_class = ArtistSerializer
    pagination_class = StandardPagination
    permission_classes = []
    
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


class ArtistRegisterView(RegisterView):
    serializer_class = RegisterArtistSerializer