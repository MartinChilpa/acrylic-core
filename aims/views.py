import requests
from django.conf import settings

from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status


class SimilarityViewSet(ViewSet):

    def create(self, request):

        youtube_url = request.data.get("youtube_url")
        page = request.data.get("page", 1)

        if not youtube_url:
            return Response(
                {"detail": "youtube_url is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        aims_url = "https://api.aimsapi.com/v1/query/by-url"

        payload = {
            "link": youtube_url,
            "page": page,
            "page_size": 20
        }

        headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Authorization": settings.AIMS_API_SECRET
        }

        response = requests.post(
            aims_url,
            json=payload,
            headers=headers
        )

        return Response(response.json(), status=response.status_code)