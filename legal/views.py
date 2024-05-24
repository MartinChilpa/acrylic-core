from rest_framework import viewsets, filters, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django_filters import rest_framework as rest_filters
from common.api.pagination import StandardPagination
from artist.permissions import IsArtistOwner
from legal.models import SplitSheet, PublishingSplit, MasterSplit
from legal.serializers import SplitSheetSerializer,SplitSheetReadSerializer, PublishingSplitSerializer, MasterSplitSerializer
#from rest_framework.metadata import SimpleMetadata


class SplitSheetFilter(rest_filters.FilterSet):
    isrc = rest_filters.CharFilter(field_name='isrc', lookup_expr='icontains')
    is_signed = rest_filters.BooleanFilter(method='filter_signed_present')

    def filter_signed_present(self, queryset, name, value):
        return queryset
        if value:
            return queryset.exclude(signed=None)
        else:
            return queryset.filter(signed=None)

    class Meta:
        model = SplitSheet
        fields = ['isrc', 'is_signed']


class MySplitSheetViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsArtistOwner]
    serializer_class = SplitSheetSerializer
    queryset = SplitSheet.objects.none()
    lookup_field = 'uuid'
    pagination_class = StandardPagination
    filter_backends = [rest_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SplitSheetFilter
    search_fields = ['isrc', 'track_name', 'track__name', 'track__uuid']
    ordering_fields = ['created', 'updated']
    #metadata_class = SimpleMetadata

    def get_queryset(self):
        return self.request.user.artist.split_sheets.order_by('-created')

    def perform_create(self, serializer):
        serializer.save(artist=self.request.user.artist)

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return SplitSheetReadSerializer
        return SplitSheetSerializer

    @extend_schema(
        responses={201: None},
        methods=['POST'],
        description="Request track split sheet signatures to all master/publishing split owners via Drobpox Sign.",
    )
    @action(detail=True, methods=['post'], url_path='request-signatures')
    def request_split_signatures(self, request, uuid=None):
        split_sheet = self.get_object()
        # todo: check if there are any splits first
        # generate document and send it to ...
        split_sheet.request_signatures()
        return Response({"detail": "Split sheet signatures requested."}, status=status.HTTP_200_OK)
