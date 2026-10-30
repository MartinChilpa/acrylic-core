import hashlib
import logging

from django.core.cache import cache
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import permissions, status
from spotify.engine import spotify_client
from spotify.serializers import TrackPreviewSerializer, TrackSearchResultSerializer

logger = logging.getLogger(__name__)

SEARCH_DEFAULT_LIMIT = 5
SEARCH_MAX_LIMIT = 10
SEARCH_MIN_QUERY_LENGTH = 2
SEARCH_CACHE_TIMEOUT = 60 * 10  # 10 min


class TrackPreviewViewSet(ViewSet):
    lookup_field = 'isrc'

    def retrieve(self, request, isrc=None):
        spotify = spotify_client()
        results = spotify.search(q=f'isrc:{isrc}', type='track')

        #print(results)

        tracks = [t for t in results['tracks']['items'] if t['external_ids']['isrc'] == isrc]
        if len(tracks) > 0:
            track_data = tracks[0]
            artist_data = track_data['artists'][0]

            try:
                image_url = track_data['album']['images'][0]['url']
            except KeyError:
                image_url = ''
            data = {
                'isrc': track_data['external_ids']['isrc'],
                'name': track_data['name'],
                'artist': artist_data['name'],
                'image': image_url,
                'spotify_url': track_data['external_urls']['spotify'],
                'spotify_id': track_data['id'],
                'duration': track_data['duration_ms'],
            }

            serializer = TrackPreviewSerializer(data=data)
            if serializer.is_valid():
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'No tracks found'})


def _smallest_image(images, min_size=64):
    # smallest album image that is at least min_size px wide
    candidates = [i for i in images or [] if (i.get('width') or 0) >= min_size]
    if not candidates:
        return ''
    return min(candidates, key=lambda i: i['width'])['url']


class TrackSearchViewSet(ViewSet):
    """
    Free-text track search on Spotify, used for the similarity search suggestions.

    GET /api/v1/spotify/search/?q=<text>&limit=<n>
    """
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        q = ' '.join(request.query_params.get('q', '').split())
        if len(q) < SEARCH_MIN_QUERY_LENGTH:
            return Response({'results': []})

        try:
            limit = int(request.query_params.get('limit', SEARCH_DEFAULT_LIMIT))
        except ValueError:
            limit = SEARCH_DEFAULT_LIMIT
        limit = max(1, min(limit, SEARCH_MAX_LIMIT))

        cache_key = f'spotify:search:{limit}:{hashlib.sha1(q.lower().encode()).hexdigest()}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response({'results': cached})

        try:
            results = spotify_client().search(q=q, type='track', limit=limit)
            items = results['tracks']['items']
        except Exception:
            logger.exception('Spotify search failed q=%r limit=%s', q, limit)
            return Response({'detail': 'Spotify search unavailable'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        data = [
            {
                'name': t['name'],
                'artist': ', '.join(a['name'] for a in t.get('artists', [])),
                'image': _smallest_image(t.get('album', {}).get('images')),
                'spotify_url': t['external_urls']['spotify'],
                'spotify_id': t['id'],
                'isrc': (t.get('external_ids') or {}).get('isrc'),
                'duration': t['duration_ms'],
            }
            for t in items if t
        ]
        serialized = TrackSearchResultSerializer(data, many=True).data

        cache.set(cache_key, serialized, SEARCH_CACHE_TIMEOUT)
        return Response({'results': serialized})
