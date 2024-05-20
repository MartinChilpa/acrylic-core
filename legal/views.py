from rest_framework import viewsets, filters, status, permissions
from rest_framework.response import Response
from common.api.pagination import StandardPagination
from artist.permissions import IsTrackArtistOwner
from legal.models import SplitSheet, PublishingSplit, MasterSplit
from legal.serializers import SplitSheetSerializer,SplitSheetReadSerializer, PublishingSplitSerializer, MasterSplitSerializer
#from rest_framework.metadata import SimpleMetadata


class MySplitSheetViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsTrackArtistOwner]
    serializer_class = SplitSheetSerializer
    queryset = SplitSheet.objects.none()
    lookup_field = 'uuid'
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['isrc', 'track__name', 'track__uuid']
    ordering_fields = ['created', 'updated']
    #metadata_class = SimpleMetadata

    def get_queryset(self):
        return self.request.user.artist.split_sheets.all()

    def perform_create(self, serializer):
        serializer.save(artist=self.request.user.artist)

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return SplitSheetReadSerializer
        return SplitSheetSerializer
