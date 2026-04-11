import os
import re
import tempfile

import requests

from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from django.core.files import File
from django_filters import rest_framework as rest_filters
from rest_framework import viewsets, filters, permissions, status, serializers
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, inline_serializer
from drf_spectacular.types import OpenApiTypes
from taggit.models import Tag
from common.api.pagination import StandardPagination
from artist.permissions import IsArtistOwner, IsTrackArtistOwner
from artist.models import Artist
from catalog.models import Distributor, Track, Genre, Price, SyncList, SyncListTrack
from catalog.validators import validate_isrc
from catalog.serializers import (
    DistributorSerializer, TrackSerializer, MyTrackSerializer, MyTrackReadSerializer, 
    GenreSerializer, SyncListSerializer, SyncListTrackSerializer, PriceSerializer, MyPriceSerializer
)

_GDRIVE_FILE_ID_RE = re.compile(r"/file/d/(?P<id>[^/]+)")
_SPOTIFY_ARTIST_ID_RE = re.compile(r"/artist/(?P<id>[A-Za-z0-9]+)")
_SPOTIFY_ARTIST_URI_RE = re.compile(r"^spotify:artist:(?P<id>[A-Za-z0-9]+)$", re.IGNORECASE)


def _maybe_google_drive_direct_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        return url
    match = _GDRIVE_FILE_ID_RE.search(url)
    if not match:
        return url
    file_id = match.group("id")
    return f"https://drive.google.com/uc?export=download&id={file_id}"


class SaveTrackToS3Serializer(serializers.Serializer):
    artist_spotify_id = serializers.CharField(required=False, allow_blank=True)
    artist_spotify_url = serializers.CharField(required=False, allow_blank=True)
    spotify_url = serializers.CharField(required=False, allow_blank=True)
    isrc = serializers.CharField()
    source_url = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True)

    def validate_isrc(self, value):
        value = (value or "").strip().upper()
        validate_isrc(value)
        return value


class SaveTrackToS3BulkItemSerializer(serializers.Serializer):
    mp3 = serializers.CharField()
    isrc = serializers.CharField()
    # Optional, but required unless label has exactly one artist or you pass an artist URL.
    artist_spotify_id = serializers.CharField(required=False, allow_blank=True)
    artist_spotify_url = serializers.CharField(required=False, allow_blank=True)
    # Optional; can be a track or artist URL. If it's an artist URL we can infer artist_spotify_id.
    spotify_url = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True)

    def validate_isrc(self, value):
        value = (value or "").strip().upper()
        validate_isrc(value)
        return value


class SaveTracksToS3BulkSerializer(serializers.Serializer):
    tracks = serializers.ListField(child=SaveTrackToS3BulkItemSerializer())


def _pick_uploaded_file(request):
    return (
        request.FILES.get("file")
        or request.FILES.get("file_mp3")
        or request.FILES.get("mp3")
        or request.FILES.get("track")
    )


def _download_to_tempfile(url: str, *, suffix=".mp3") -> str:
    url = _maybe_google_drive_direct_url(url)
    with requests.get(url, stream=True, timeout=(10, 120), allow_redirects=True) as resp:
        resp.raise_for_status()
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    tmp.write(chunk)
        finally:
            tmp.close()
    return tmp.name


def _extract_spotify_artist_id(value):
    if not isinstance(value, str):
        return None
    v = value.strip()
    if not v:
        return None
    m = _SPOTIFY_ARTIST_URI_RE.match(v)
    if m:
        return m.group("id")
    v_no_q = v.split("?", 1)[0].split("#", 1)[0]
    m = _SPOTIFY_ARTIST_ID_RE.search(v_no_q)
    if m:
        return m.group("id")
    return None


def _save_label_track_audio_to_s3(*, label, artist, isrc, uploaded, label_slug, artist_spotify_id, name=""):
    s3_key = f"tracks/{label_slug}/{artist_spotify_id}/{isrc}.mp3"
    with transaction.atomic():
        track, created = Track.objects.get_or_create(
            artist=artist,
            isrc=isrc,
            defaults={"name": (name or "").strip()},
        )

        if track.file_wav and track.file_wav.name and track.file_wav.name != s3_key:
            try:
                track.file_wav.delete(save=False)
            except Exception:
                pass

        try:
            track.file_wav.storage.delete(s3_key)
        except Exception:
            pass

        track._upload_as_label = True
        track._label_slug = label_slug
        track._artist_spotify_id = artist_spotify_id
        track._label_fallback = label_slug
        track.file_wav.save(f"{isrc}.mp3", uploaded, save=False)

        Track.objects.filter(pk=track.pk).update(file_wav=track.file_wav.name, updated=timezone.now())

        # Ensure label ingestion still triggers external-id enrichment.
        # - On create, Track.save() already enqueues these tasks.
        # - On update/re-upload, enqueue them here (without calling Track.save()).
        if not created:
            try:
                from spotify.tasks import load_spotify_id
                from chartmetric.tasks import load_chartmetric_ids

                transaction.on_commit(lambda: load_spotify_id.delay(track.id, load_data=True))
                transaction.on_commit(lambda: load_chartmetric_ids.delay(track.id))
            except Exception:
                pass

    return {"track_uuid": track.uuid, "created": created, "s3_key": track.file_wav.name}


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

    @extend_schema(
        request=SaveTrackToS3Serializer,
        responses={200: inline_serializer(
            name="SaveTrackToS3Response",
            fields={
                "track_uuid": serializers.UUIDField(format="hex_verbose"),
                "created": serializers.BooleanField(),
                "s3_key": serializers.CharField(),
            },
        )},
        methods=["POST"],
        description=(
            "Label-only: upload/download an MP3 and persist it to S3 under "
            "`tracks/<label_slug>/<artist_spotify_id>/<isrc>.mp3`."
        ),
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="save-to-s3",
        permission_classes=[permissions.IsAuthenticated],
        authentication_classes=[BasicAuthentication, JWTAuthentication],
        parser_classes=[MultiPartParser, FormParser],
    )
    def save_to_s3(self, request):
        label = getattr(request.user, "label", None)
        if label is None:
            return Response({"detail": "Label profile is required."}, status=status.HTTP_403_FORBIDDEN)

        ser = SaveTrackToS3Serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        artist_spotify_id = (ser.validated_data.get("artist_spotify_id") or "").strip()
        artist_spotify_url = (ser.validated_data.get("artist_spotify_url") or "").strip()
        spotify_url = (ser.validated_data.get("spotify_url") or "").strip()
        isrc = ser.validated_data["isrc"]
        source_url = (ser.validated_data.get("source_url") or "").strip()

        if not artist_spotify_id:
            artist_spotify_id = _extract_spotify_artist_id(artist_spotify_url) or _extract_spotify_artist_id(spotify_url)
        if not artist_spotify_id:
            return Response(
                {"detail": "Provide artist_spotify_id or an artist spotify url (artist_spotify_url or spotify_url)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        artist = Artist.objects.filter(spotify_id=artist_spotify_id).first()
        if artist is None:
            return Response({"detail": "Artist not found for artist_spotify_id"}, status=status.HTTP_404_NOT_FOUND)

        if artist.label_id != label.id:
            return Response({"detail": "Artist does not belong to this label"}, status=status.HTTP_403_FORBIDDEN)

        uploaded = _pick_uploaded_file(request)
        tmp_path = None
        try:
            if uploaded is None:
                if not source_url:
                    return Response(
                        {"detail": "Provide either a multipart file (file/file_mp3) or source_url"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                tmp_path = _download_to_tempfile(source_url, suffix=".mp3")
                with open(tmp_path, "rb") as fp:
                    uploaded = File(fp, name=f"{isrc}.mp3")
                    label_slug = (getattr(label, "slug", None) or "").strip() or slugify(getattr(label, "label_name", "") or "")
                    if not label_slug:
                        label_slug = "acrylic"

                    out = _save_label_track_audio_to_s3(
                        label=label,
                        artist=artist,
                        isrc=isrc,
                        uploaded=uploaded,
                        label_slug=label_slug,
                        artist_spotify_id=artist_spotify_id,
                        name=(ser.validated_data.get("name") or "").strip(),
                    )
                    return Response(out, status=status.HTTP_200_OK)

            label_slug = (getattr(label, "slug", None) or "").strip() or slugify(getattr(label, "label_name", "") or "")
            if not label_slug:
                label_slug = "acrylic"
            out = _save_label_track_audio_to_s3(
                label=label,
                artist=artist,
                isrc=isrc,
                uploaded=uploaded,
                label_slug=label_slug,
                artist_spotify_id=artist_spotify_id,
                name=(ser.validated_data.get("name") or "").strip(),
            )
            return Response(out, status=status.HTTP_200_OK)
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    @extend_schema(
        request=SaveTracksToS3BulkSerializer,
        responses={200: inline_serializer(
            name="SaveTracksToS3BulkResponse",
            fields={
                "count": serializers.IntegerField(),
                "saved": serializers.IntegerField(),
                "errors": serializers.ListField(child=serializers.DictField()),
                "results": serializers.ListField(child=serializers.DictField()),
            },
        )},
        methods=["POST"],
        description="Label-only: bulk save MP3s to S3 under `tracks/<label_slug>/<artist_spotify_id>/<isrc>.mp3`.",
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="save-to-s3-bulk",
        permission_classes=[permissions.IsAuthenticated],
        authentication_classes=[BasicAuthentication, JWTAuthentication],
    )
    def save_to_s3_bulk(self, request):
        label = getattr(request.user, "label", None)
        if label is None:
            return Response({"detail": "Label profile is required."}, status=status.HTTP_403_FORBIDDEN)

        ser = SaveTracksToS3BulkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tracks = ser.validated_data.get("tracks") or []

        label_slug = (getattr(label, "slug", None) or "").strip() or slugify(getattr(label, "label_name", "") or "")
        if not label_slug:
            label_slug = "acrylic"

        label_artists = list(Artist.objects.filter(label=label).only("id", "spotify_id", "label_id"))
        label_artist_by_spotify = {a.spotify_id: a for a in label_artists if a.spotify_id}

        results = []
        errors = []
        enqueued = 0

        for idx, item in enumerate(tracks):
            try:
                isrc = item["isrc"]
                source_url = (item.get("mp3") or "").strip()
                if not source_url:
                    raise ValueError("mp3 is required")

                artist_spotify_id = (item.get("artist_spotify_id") or "").strip()
                artist_spotify_url = (item.get("artist_spotify_url") or "").strip()
                spotify_url = (item.get("spotify_url") or "").strip()

                if not artist_spotify_id:
                    artist_spotify_id = _extract_spotify_artist_id(artist_spotify_url) or _extract_spotify_artist_id(spotify_url)

                if not artist_spotify_id:
                    if len(label_artists) == 1 and label_artists[0].spotify_id:
                        artist_spotify_id = label_artists[0].spotify_id
                    else:
                        raise ValueError("artist_spotify_id (or artist_spotify_url) is required")

                artist = label_artist_by_spotify.get(artist_spotify_id)
                if artist is None:
                    artist = Artist.objects.filter(spotify_id=artist_spotify_id).first()
                    if artist is None:
                        raise ValueError("Artist not found for artist_spotify_id")
                    if artist.label_id != label.id:
                        raise ValueError("Artist does not belong to this label")

                # Create the Track row immediately (fast) so the client can see UUIDs,
                # then enqueue the slow download+upload work to Celery to avoid Heroku H12.
                track, created = Track.objects.get_or_create(
                    artist=artist,
                    isrc=isrc,
                    defaults={"name": (item.get("name") or "").strip()},
                )
                if not created and (item.get("name") or "").strip() and not (track.name or "").strip():
                    Track.objects.filter(pk=track.pk).update(name=(item.get("name") or "").strip(), updated=timezone.now())

                from catalog.tasks import ingest_track_audio_from_url

                async_res = ingest_track_audio_from_url.delay(
                    track.id,
                    source_url,
                    label_slug=label_slug,
                    artist_spotify_id=artist_spotify_id,
                    name=(item.get("name") or "").strip(),
                )
                enqueued += 1
                results.append(
                    {
                        "index": idx,
                        "track_id": track.id,
                        "track_uuid": str(track.uuid),
                        "created": created,
                        "task_id": getattr(async_res, "id", None),
                    }
                )
            except Exception as e:
                errors.append({"index": idx, "detail": str(e)})

        return Response(
            {
                "count": len(tracks),
                "saved": enqueued,  # backwards-compatible key
                "enqueued": enqueued,
                "mode": "async",
                "errors": errors,
                "results": results,
            },
            status=status.HTTP_202_ACCEPTED,
        )
    
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
        
    def finalize_response(self, request, response, *args, **kwargs):

        
        return super().finalize_response(request, response, *args, **kwargs)

    @extend_schema(
        methods=["GET"],
        description=(
            "Fetch Chartmetric track virality for this track via "
            "`track/{id}/chartmetric/stats/most-history` and return only the first `value` found."
        ),
        responses={200: OpenApiTypes.FLOAT},
    )
    @action(detail=True, methods=["get"], url_path="chartmetric/score-history")
    def chartmetric_score_history(self, request, uuid=None):
        track = self.get_object()
        if not getattr(track, "chartmetric_id", ""):
            return Response({"detail": "Track has no chartmetric_id"}, status=status.HTTP_400_BAD_REQUEST)

        from chartmetric.engine import Chartmetric

        cm = Chartmetric()
        if not cm.authenticate():
            return Response({"detail": "Chartmetric authentication failed"}, status=status.HTTP_502_BAD_GATEWAY)

        value = cm.get_track_virality(track.chartmetric_id)
        if isinstance(value, dict) and value.get("error"):
            return Response(value, status=status.HTTP_502_BAD_GATEWAY)
        return Response(value, status=status.HTTP_200_OK)


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
