import requests
import logging
from django.conf import settings

from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status

from catalog.models import Track

logger = logging.getLogger(__name__)

# Useful for frontend dev/testing without calling AIMS.
DUMMY_SIMILARITY_RESPONSE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [{
        "id_client": 124,
        "track_name": "Dummy Track",
        "artist_canonical": "Dummy Artist",
        "duration": 241,
        "release_year": 2024,
        "moods": ["happy"],
        "cover_image": None,
        "file_mp3": None,
        "spotify_followers": 0,
        "instagram_followers": 0,
        "youtube_followers": 0,
        "tiktok_followers": 0,
        "insta_followers_spotify_followers": {"instagram_followers": 0, "spotify_followers": 0},
        "chartmetric_instagram_demographics": None,
        "chartmetric_instagram_top_cities": None,
        "chartmetric_instagram_top_countries": None,
    }],
}



def _extract_aims_client_id(payload):
    """
    Best-effort extraction of a numeric AIMS id from a JSON payload.
    """
    if not isinstance(payload, dict):
        return None

    direct_keys = (
        "id_client",
        "idClient",
        "client_id",
        "clientId",
        "aims_id",
        "aimsId",
        "id",
        "track_id",
        "trackId",
    )
    for key in direct_keys:
        value = payload.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)

    for container_key in ("data", "result", "obj"):
        value = payload.get(container_key)
        if isinstance(value, dict):
            extracted = _extract_aims_client_id(value)
            if extracted is not None:
                return extracted

    for list_key in ("results", "items", "tracks"):
        value = payload.get(list_key)
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, dict):
                extracted = _extract_aims_client_id(first)
                if extracted is not None:
                    return extracted

    return None


def _extract_first_list(payload):
    """
    Best-effort extraction of a list of results from AIMS' JSON response.
    """
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return None

    for list_key in ("results", "items", "tracks", "data"):
        value = payload.get(list_key)
        if isinstance(value, list):
            return value

    for container_key in ("data", "result", "obj"):
        value = payload.get(container_key)
        if isinstance(value, dict):
            extracted = _extract_first_list(value)
            if extracted is not None:
                return extracted

    # fallback: search nested structures
    for nested in payload.values():
        extracted = _extract_first_list(nested)
        if extracted is not None:
            return extracted

    return None


def _as_int(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _as_str(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _normalize_moods(value):
    if value is None:
        return []
    if isinstance(value, str):
        # Accept either a single mood or a comma-separated string.
        parts = [p.strip() for p in value.split(",")]
        return [p for p in parts if p]
    if isinstance(value, dict):
        # Common shapes: {"moods": [...]} or {"items": [...]}.
        for key in ("moods", "mood", "items", "results", "data"):
            nested = value.get(key)
            if nested is not None:
                return _normalize_moods(nested)
        # Or {"name": "..."}.
        if "name" in value:
            return _normalize_moods(value.get("name"))
        return []
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                if "name" in item:
                    out.extend(_normalize_moods(item.get("name")))
                elif "label" in item:
                    out.extend(_normalize_moods(item.get("label")))
        return out
    return []


def _extract_artist_name(item):
    if not isinstance(item, dict):
        return None

    for key in ("artist_canonical", "artist_name", "artistName"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    # Common alternative shapes:
    # - {"artist": "Name"}
    # - {"artist": {"name": "Name"}}
    artist_value = item.get("artist")
    if isinstance(artist_value, dict):
        value = artist_value.get("name")
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(artist_value, str) and artist_value.strip():
        return artist_value.strip()

    # - {"artists": [{"name": "Name"}, ...]}
    artists_value = item.get("artists")
    if isinstance(artists_value, list) and artists_value:
        first = artists_value[0]
        if isinstance(first, dict):
            value = first.get("name")
            if isinstance(value, str) and value.strip():
                return value.strip()
        if isinstance(first, str) and first.strip():
            return first.strip()

    # - {"artist_names": ["Name", ...]}
    artist_names = item.get("artist_names") or item.get("artistNames")
    if isinstance(artist_names, list) and artist_names:
        first = artist_names[0]
        if isinstance(first, str) and first.strip():
            return first.strip()

    return None


def _simplify_aims_item(item):
    """
    Map a single AIMS result into the compact schema our frontend needs.
    """
    if not isinstance(item, dict):
        return None

    id_client = _extract_aims_client_id(item)

    track_name = item.get("track_name")
    if track_name is None:
        track_name = item.get("name")

    artist_canonical = _extract_artist_name(item)

    duration = item.get("duration")
    if duration is None:
        duration = item.get("duration_seconds")
    if duration is None:
        duration = item.get("duration_sec")
    duration = _as_int(duration)

    release_year = item.get("release_year")
    if release_year is None:
        release_date = _as_str(item.get("release_date") or item.get("released"))
        if release_date and len(release_date) >= 4 and release_date[:4].isdigit():
            release_year = int(release_date[:4])
    release_year = _as_int(release_year)

    moods_raw = None
    for key in ("moods", "mood", "mood_tags", "moodTags", "mood_labels", "moodLabels"):
        if item.get(key) is not None:
            moods_raw = item.get(key)
            break

    if moods_raw is None:
        auto = item.get("auto_tagging_output")
        if isinstance(auto, dict):
            moods_raw = auto.get("moods") or auto.get("mood")

    moods = _normalize_moods(moods_raw)
        
        

    file_wav = None
    file_mp3 = None
    waveform = None
    track_name_track = None
    cover_image = None
    spotify_followers = 0
    instagram_followers = 0
    youtube_followers = 0
    tiktok_followers = 0
    chartmetric_instagram_demographics = None
    chartmetric_instagram_top_cities = None
    chartmetric_instagram_top_countries = None
    if id_client is not None:
        track = (
            Track.objects.select_related("artist")
            .filter(aims_id=id_client)
            .only(
                "file_wav",
                "file_mp3",
                "waveform",
                "cover_image",
                "name",
                "artist__name",
                "artist__spotify_followers",
                "artist__instagram_followers",
                "artist__youtube_followers",
                "artist__tiktok_followers",
                "artist__chartmetric_instagram_demographics",
                "artist__chartmetric_instagram_top_cities",
                "artist__chartmetric_instagram_top_countries",
            )
            .first()
        )
        file_wav = track.file_wav.url if track and track.file_wav else None
        file_mp3 = track.file_mp3.url if track and track.file_mp3 else None
        waveform = track.waveform.url if track and track.waveform else None
        cover_image = track.cover_image.url if track and track.cover_image else None
        track_name_track = track.name if track and track.name else None
        # Prefer our internal Artist name when we have it.
        if track and getattr(track, "artist", None) and track.artist:
            if track.artist.name:
                artist_canonical = track.artist.name

            spotify_followers = getattr(track.artist, "spotify_followers", 0) or 0
            instagram_followers = getattr(track.artist, "instagram_followers", 0) or 0
            youtube_followers = getattr(track.artist, "youtube_followers", 0) or 0
            tiktok_followers = getattr(track.artist, "tiktok_followers", 0) or 0

            chartmetric_instagram_demographics = getattr(track.artist, "chartmetric_instagram_demographics", None)
            chartmetric_instagram_top_cities = getattr(track.artist, "chartmetric_instagram_top_cities", None)
            chartmetric_instagram_top_countries = getattr(track.artist, "chartmetric_instagram_top_countries", None)


    return {
        "id_client": id_client,
        "track_name": _as_str(track_name),
        "artist_canonical": _as_str(artist_canonical),
        "duration": duration,
        "release_year": release_year,
        "moods": moods,
        "cover_image": cover_image,
        "file_wav": file_wav,
        "file_mp3": file_mp3,
        "waveform": waveform,
        "track_name_track": track_name_track,
        "spotify_followers": spotify_followers,
        "instagram_followers": instagram_followers,
        "youtube_followers": youtube_followers,
        "tiktok_followers": tiktok_followers,
        "chartmetric_instagram_demographics": chartmetric_instagram_demographics,
        "chartmetric_instagram_top_cities": chartmetric_instagram_top_cities,
        "chartmetric_instagram_top_countries": chartmetric_instagram_top_countries,
    }


def _simplify_aims_payload(payload):
    items = _extract_first_list(payload) or []
    simplified = []
    for item in items:
        mapped = _simplify_aims_item(item)
        if mapped is not None:
            simplified.append(mapped)
    return {"count": len(simplified), "results": simplified}


class SimilarityViewSet(ViewSet):

    def create(self, request):
        # Handy for frontend dev/testing without calling AIMS.
        if request.query_params.get("dummy") == "1":
            return Response(DUMMY_SIMILARITY_RESPONSE, status=status.HTTP_200_OK)

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
            "X-Client-Id": settings.AIMS_CLIENT_ID,
            "X-Client-Secret": settings.AIMS_API_SECRET
        }

        response = requests.post(
            aims_url,
            json=payload,
            headers=headers
        )

        try:
            aims_payload = response.json()
        except ValueError:
            return Response(
                {"detail": "Invalid JSON received from AIMS."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Return only the fields our frontend needs.
        return Response(_simplify_aims_payload(aims_payload), status=response.status_code)
