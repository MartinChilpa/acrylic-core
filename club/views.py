from django.conf import settings

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from club.models import Club
from club.serializers import TeamConfigSerializer, TeamPlayerSerializer


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
