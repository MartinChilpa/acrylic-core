from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from spotify.engine import spotify_client
from spotify.serializers import TrackPreviewSerializer


class TrackPreviewViewSet(ViewSet):
    lookup_field = 'isrc'

    def retrieve(self, request, isrc=None):
        spotify = spotify_client()
        results = spotify.search(q=f'isrc:{isrc}', type='track')

        print(results)

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
