from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from catalog.models import Track  # Ensure the correct import path
from artist.permissions import IsTrackArtistOwner
from legal.models import SplitSheet, PublishingSplit, MasterSplit
from legal.serializers import SplitSheetSerializer, PublishingSplitSerializer, MasterSplitSerializer


class SplitSheetViewSet(viewsets.ModelViewSet):
    serializer_class = SplitSheetSerializer
    permission_classes = [permissions.IsAuthenticated, IsTrackArtistOwner]
    queryset = SplitSheet.objects.none()

    def get_queryset(self):
        track_id = self.kwargs.get('track_id')
        if track_id is not None:
            return self.queryset.filter(track_id=track_id, track__artist=self.request.user.artist)
        return self.queryset.none()  # Return an empty queryset if no track_id is provided

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.serializer_class(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=204)
