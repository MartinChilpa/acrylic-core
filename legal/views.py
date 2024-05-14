from rest_framework import viewsets, filters, status, permissions
from rest_framework.response import Response
from common.api.pagination import StandardPagination
from artist.permissions import IsTrackArtistOwner
from legal.models import SplitSheet, PublishingSplit, MasterSplit
from legal.serializers import SplitSheetSerializer, PublishingSplitSerializer, MasterSplitSerializer


class MySplitSheetViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsTrackArtistOwner]
    serializer_class = SplitSheetSerializer
    queryset = SplitSheet.objects.none()
    lookup_field = 'uuid'
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['track__name']
    ordering_fields = ['created', 'updated']

    def get_queryset(self):
        return self.request.user.artist.split_sheets.all()

    def perform_create(self, serializer):
        serializer.save(artist=self.request.user.artist)
