from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from catalog.models import Track
from club.models import Club, TrackFavorite
from club.serializers import TeamConfigSerializer, TeamPlayerSerializer, TrackFavoriteSerializer


class ClubFavoritesViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TrackFavoriteSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "club") and user.club:
            return TrackFavorite.objects.filter(club=user.club).select_related("track", "track__artist")
        return TrackFavorite.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"count": queryset.count(), "results": serializer.data})

    @action(detail=False, methods=["post"], url_path="toggle")
    def toggle(self, request, *args, **kwargs):
        track_uuid = request.data.get("track_uuid")
        if not track_uuid:
            return Response({"detail": "track_uuid is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not hasattr(user, "club") or not user.club:
            return Response({"detail": "No club found for this user."}, status=status.HTTP_400_BAD_REQUEST)

        track = get_object_or_404(Track, uuid=track_uuid)
        favorite_qs = TrackFavorite.objects.filter(club=user.club, track=track)
        is_favorited = favorite_qs.exists()

        if is_favorited:
            favorite_qs.delete()
        else:
            TrackFavorite.objects.create(club=user.club, track=track)

        return Response({"is_favorited": not is_favorited})


class TeamViewSet(viewsets.GenericViewSet):
    queryset = Club.objects.all()
    lookup_field = "slug"
    authentication_classes = []
    permission_classes = []

    @action(detail=True, methods=["get"], url_path="config")
    def config(self, request, *args, **kwargs):
        club = self.get_object()
        if settings.DEBUG:
            print(f"Club tagline ({club.slug}): {(club.tagline or '').strip()}", flush=True)
        serializer = TeamConfigSerializer(club)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="players")
    def players(self, request, *args, **kwargs):
        club = self.get_object()
        players_qs = club.players.filter(is_active=True).order_by("name")
        serializer = TeamPlayerSerializer(players_qs, many=True)
        return Response({"team_slug": club.slug, "players": serializer.data})
