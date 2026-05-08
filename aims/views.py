import requests
import logging
import copy
import time
import re
from urllib.parse import quote, unquote, urlparse
from django.conf import settings

from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

import boto3

from catalog.models import Track
from spotify.engine import spotify_client
from chartmetric.dummy import (
    DEFAULT_TRACK_VIRALITY,
    DEFAULT_ARTIST_INSTAGRAM_FOLLOWERS,
    DEFAULT_ARTIST_SPOTIFY_FOLLOWERS,
    DEFAULT_ARTIST_TIKTOK_FOLLOWERS,
    DEFAULT_ARTIST_YOUTUBE_FOLLOWERS,
    DEFAULT_CHARTMETRIC_INSTAGRAM_DEMOGRAPHICS,
    DEFAULT_CHARTMETRIC_INSTAGRAM_TOP_CITIES,
    DEFAULT_CHARTMETRIC_INSTAGRAM_TOP_COUNTRIES,
    DEFAULT_CHARTMETRIC_INSTAGRAM_SPORTS_FIT_PERCENT,
)

logger = logging.getLogger(__name__)

# Spotify helpers (track URLs/URIs)
_SPOTIFY_TRACK_ID_RE = re.compile(r"/track/(?P<id>[A-Za-z0-9]+)")
_SPOTIFY_TRACK_URI_RE = re.compile(r"^spotify:track:(?P<id>[A-Za-z0-9]+)$", re.IGNORECASE)


def _extract_spotify_track_id(value):
    if not isinstance(value, str):
        return None
    v = value.strip()
    if not v:
        return None
    m = _SPOTIFY_TRACK_URI_RE.match(v)
    if m:
        return m.group("id")
    v_no_q = v.split("?", 1)[0].split("#", 1)[0]
    m = _SPOTIFY_TRACK_ID_RE.search(v_no_q)
    if m:
        return m.group("id")
    # raw id fallback
    if re.fullmatch(r"[A-Za-z0-9]{10,40}", v):
        return v
    return None


def _extract_s3_key_from_url(url: str) -> str | None:
    """
    Best-effort extraction of an object key from a URL (presigned or public).

    We intentionally keep this conservative: only the URL path is used.
    """
    if not isinstance(url, str):
        return None
    raw = url.strip()
    if not raw:
        return None
    try:
        parsed = urlparse(raw)
    except Exception:
        return None
    path = (parsed.path or "").strip()
    if not path:
        return None
    key = unquote(path.lstrip("/"))
    return key or None


def _sanitize_attachment_filename(filename: str) -> str:
    """
    Sanitize a user-provided filename so it is safe to embed in a
    Content-Disposition header.
    """
    name = (filename or "").strip()
    name = name.replace("\r", "").replace("\n", "")
    name = name.split("/")[-1].split("\\")[-1].strip()
    if not name:
        name = "download"
    return name[:200]


def _build_content_disposition(filename: str) -> str:
    safe = _sanitize_attachment_filename(filename)
    ascii_fallback = safe.encode("ascii", "ignore").decode("ascii") or "download"
    ascii_fallback = re.sub(r'[\x00-\x1f\x7f"]+', "_", ascii_fallback)
    utf8_encoded = quote(safe, safe="")
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{utf8_encoded}'


def _s3_client():
    kwargs = {}
    region = getattr(settings, "AWS_S3_REGION_NAME", "") or None
    if region:
        kwargs["region_name"] = region
    endpoint_url = getattr(settings, "AWS_S3_ENDPOINT_URL", "") or None
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    access_key = getattr(settings, "AWS_ACCESS_KEY_ID", "") or ""
    secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", "") or ""
    if access_key and secret_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key
    return boto3.client("s3", **kwargs)


class AimsDownloadUrlInputSerializer(serializers.Serializer):
    key = serializers.CharField(required=False, allow_blank=False, trim_whitespace=True)
    url = serializers.CharField(required=False, allow_blank=False, trim_whitespace=True)
    filename = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True, max_length=200)

    def validate(self, attrs):
        key = attrs.get("key")
        url = attrs.get("url")
        if not key and not url:
            raise serializers.ValidationError("Either 'key' or 'url' is required.")

        # Accept legacy clients that pass a full URL in `key`.
        if isinstance(key, str) and "://" in key:
            url = key
            key = None

        if not key and url:
            extracted = _extract_s3_key_from_url(url)
            if not extracted:
                raise serializers.ValidationError({"url": "Could not extract key from url."})
            key = extracted

        key = (key or "").strip().lstrip("/")

        # Some URL shapes include the bucket as the first path segment:
        #   https://s3.<region>.amazonaws.com/<bucket>/<key>
        bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "") or ""
        if bucket and key.startswith(f"{bucket}/"):
            key = key[len(bucket) + 1 :]

        if not key:
            raise serializers.ValidationError({"key": "Invalid key."})
        if not key.startswith("tracks/"):
            raise serializers.ValidationError({"key": "Key must start with 'tracks/'."})
        if ".." in key or "\x00" in key:
            raise serializers.ValidationError({"key": "Invalid key."})

        attrs["key"] = key
        attrs["filename"] = _sanitize_attachment_filename(attrs.get("filename", ""))
        return attrs

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
        "track_virality": None,
        "price_id": None,
        "price_uuid": None,
        "moods": ["happy"],
        "highlights": [],
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

# Provisional shortcut for frontend dev/testing:
# If SimilarityPrompt receives text == "test" (query param or body), return 3 dummy results.
DUMMY_PROMPT_TEST_RESPONSE = {
    "count": 3,
    "next": None,
    "previous": None,
    "results": [
        {
            "id_client": 124,
            "track_name": "Dummy Track 1",
            "artist_canonical": "Dummy Artist",
            "duration": 241,
            "release_year": 2024,
            "track_virality": None,
            "price_id": None,
            "price_uuid": None,
            "moods": ["happy"],
            "highlights": [{"duration": 12.5, "offset": 30.0}],
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
        },
        {
            "id_client": 125,
            "track_name": "Dummy Track 2",
            "artist_canonical": "Dummy Artist",
            "duration": 198,
            "release_year": 2023,
            "track_virality": None,
            "price_id": None,
            "price_uuid": None,
            "moods": ["chill", "dreamy"],
            "highlights": [{"duration": 8.0, "offset": 75.0}],
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
        },
        {
            "id_client": 126,
            "track_name": "Dummy Track 3",
            "artist_canonical": "Dummy Artist",
            "duration": 215,
            "release_year": 2022,
            "track_virality": None,
            "price_id": None,
            "price_uuid": None,
            "moods": ["energetic"],
            "highlights": [{"duration": 10.0, "offset": 120.0}],
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
        },
    ],
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


def _normalize_highlights(value):
    """
    Normalize AIMS highlights into:
      [{"duration": float, "offset": float}, ...]
    """
    if value is None:
        return []
    if isinstance(value, dict):
        for key in ("highlights", "items", "results", "data"):
            if key in value:
                return _normalize_highlights(value.get(key))
        return []
    if isinstance(value, list):
        out = []
        for item in value:
            if not isinstance(item, dict):
                continue
            duration = item.get("duration")
            offset = item.get("offset")
            if duration is None or offset is None:
                continue
            try:
                out.append({"duration": float(duration), "offset": float(offset)})
            except (TypeError, ValueError):
                continue
        return out
    return []


def _extract_artist_name(item):
    if not isinstance(item, dict):
        return None

    for key in ("artist_canonical", "artist_name", "artistName"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
            
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


def _simplify_aims_item(item, *, debug_moods=False):
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

    match_score = None
    for key in ("match_score", "matchScore", "score", "similarity", "similarity_score", "similarityScore"):
        if item.get(key) is None:
            continue
        try:
            match_score = float(item.get(key))
            break
        except (TypeError, ValueError):
            continue

    release_year = item.get("release_year")
    if release_year is None:
        release_date = _as_str(item.get("release_date") or item.get("released"))
        if release_date and len(release_date) >= 4 and release_date[:4].isdigit():
            release_year = int(release_date[:4])
    release_year = _as_int(release_year)
    if release_year is None:
        release_year = 2021

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
    if debug_moods:
        print("[aims] moods:", {"id_client": id_client, "track_name": _as_str(track_name), "moods": moods})

    highlights_raw = None
    for key in ("highlights", "highlight", "highlights_list", "highlightsList"):
        if item.get(key) is not None:
            highlights_raw = item.get(key)
            break
    if highlights_raw is None:
        auto = item.get("auto_tagging_output")
        if isinstance(auto, dict):
            highlights_raw = auto.get("highlights")
    highlights = _normalize_highlights(highlights_raw)

    file_wav = None
    file_mp3 = None
    waveform = None
    track_name_track = None
    cover_image = None
    spotify_followers = 0
    instagram_followers = 0
    youtube_followers = 0
    tiktok_followers = 0
    artist_country_code2 = None
    chartmetric_instagram_demographics = None
    chartmetric_instagram_top_cities = None
    chartmetric_instagram_top_countries = None
    chartmetric_instagram_sports_fit_percent = 0
    track_virality = None
    price_id = None
    price_uuid = None
    track_id = None
    track_uuid = None
    if id_client is not None:
        qs = (
            Track.objects.select_related("artist", "price")
            .only(
                "aims_id",
                "id",
                "uuid",
                "file_wav",
                "file_mp3",
                "waveform",
                "cover_image",
                "name",
                "virality",
                "price_id",
                "price__uuid",
                "artist__name",
                "artist__country",
                "artist__spotify_followers",
                "artist__instagram_followers",
                "artist__youtube_followers",
                "artist__tiktok_followers",
                "artist__chartmetric_instagram_demographics",
                "artist__chartmetric_instagram_top_cities",
                "artist__chartmetric_instagram_top_countries",
                "artist__chartmetric_instagram_sports_fit_percent",
            )
        )

        # Primary join: AIMS should return the same id_client we sent (Track.aims_id).
        track = qs.filter(aims_id=id_client).first()
        track_id = getattr(track, "id", None) if track else None
        track_uuid = str(track.uuid) if track and getattr(track, "uuid", None) else None

        if track:
            if duration is None and getattr(track, "duration", None):
                try:
                    duration = int(int(track.duration) / 1000)
                except Exception:
                    pass
            if (release_year is None or release_year == 2021) and getattr(track, "released", None):
                try:
                    release_year = int(track.released.year)
                except Exception:
                    pass

        file_wav = track.file_wav.url if track and track.file_wav else None
        file_mp3 = track.file_mp3.url if track and track.file_mp3 else None
        waveform = track.waveform.url if track and track.waveform else None
        cover_image = track.cover_image.url if track and track.cover_image else None
        track_name_track = track.name if track and track.name else None
        track_virality = getattr(track, "virality", None) if track else None
        price_id = getattr(track, "price_id", None) if track else None
        price_uuid = str(track.price.uuid) if track and getattr(track, "price", None) else None
        # Prefer our internal Artist name when we have it.
        if track and getattr(track, "artist", None) and track.artist:
            if track.artist.name:
                artist_canonical = track.artist.name
            if getattr(track.artist, "country", None):
                artist_country_code2 = str(track.artist.country)

            spotify_followers = getattr(track.artist, "spotify_followers", 0) or 0
            instagram_followers = getattr(track.artist, "instagram_followers", 0) or 0
            youtube_followers = getattr(track.artist, "youtube_followers", 0) or 0
            tiktok_followers = getattr(track.artist, "tiktok_followers", 0) or 0

            chartmetric_instagram_demographics = getattr(track.artist, "chartmetric_instagram_demographics", None)
            chartmetric_instagram_top_cities = getattr(track.artist, "chartmetric_instagram_top_cities", None)
            chartmetric_instagram_top_countries = getattr(track.artist, "chartmetric_instagram_top_countries", None)
            chartmetric_instagram_sports_fit_percent = getattr(track.artist, "chartmetric_instagram_sports_fit_percent", 0) or 0

            # Optional dummy fallbacks for demo/dev when Chartmetric hasn't populated yet.
            if bool(getattr(settings, "CHARTMETRIC_USE_DUMMY_FALLBACKS", False)):
                if not track_virality:
                    track_virality = DEFAULT_TRACK_VIRALITY
                if not spotify_followers:
                    spotify_followers = DEFAULT_ARTIST_SPOTIFY_FOLLOWERS
                if not instagram_followers:
                    instagram_followers = DEFAULT_ARTIST_INSTAGRAM_FOLLOWERS
                if not tiktok_followers:
                    tiktok_followers = DEFAULT_ARTIST_TIKTOK_FOLLOWERS
                if not youtube_followers:
                    youtube_followers = DEFAULT_ARTIST_YOUTUBE_FOLLOWERS

                if not chartmetric_instagram_demographics:
                    chartmetric_instagram_demographics = DEFAULT_CHARTMETRIC_INSTAGRAM_DEMOGRAPHICS
                if not chartmetric_instagram_top_cities:
                    chartmetric_instagram_top_cities = DEFAULT_CHARTMETRIC_INSTAGRAM_TOP_CITIES
                if not chartmetric_instagram_top_countries:
                    chartmetric_instagram_top_countries = DEFAULT_CHARTMETRIC_INSTAGRAM_TOP_COUNTRIES
                if not chartmetric_instagram_sports_fit_percent:
                    chartmetric_instagram_sports_fit_percent = DEFAULT_CHARTMETRIC_INSTAGRAM_SPORTS_FIT_PERCENT


    return {
        "id_client": id_client,
        "track_id": track_id,
        "track_uuid": track_uuid,
        "track_name": _as_str(track_name),
        "artist_canonical": _as_str(artist_canonical),
        "artist_country_code2": artist_country_code2,
        "match_score": match_score,
        "duration": duration,
        "release_year": release_year,
        "track_virality": track_virality,
        "price_id": price_id,
        "price_uuid": price_uuid,
        "moods": moods,
        "highlights": highlights,
        "cover_image": cover_image,
        "file_wav": file_wav,
        "file_mp3": file_mp3,
        "waveform": waveform,
        "waveform_url": waveform,
        "track_name_track": track_name_track,
        "spotify_followers": spotify_followers,
        "instagram_followers": instagram_followers,
        "youtube_followers": youtube_followers,
        "tiktok_followers": tiktok_followers,
        "chartmetric_instagram_demographics": chartmetric_instagram_demographics,
        "chartmetric_instagram_top_cities": chartmetric_instagram_top_cities,
        "chartmetric_instagram_top_countries": chartmetric_instagram_top_countries,
        "chartmetric_instagram_sports_fit_percent": chartmetric_instagram_sports_fit_percent,
    }


def _simplify_aims_payload(payload, *, debug_moods=False):
    items = _extract_first_list(payload) or []
    simplified = []
    for item in items:
        mapped = _simplify_aims_item(item, debug_moods=debug_moods)
        if mapped is not None:
            simplified.append(mapped)
    return {"count": len(simplified), "results": simplified}

 
class SimilarityViewSet(ViewSet):

    def _aims_query_by_url(self, *, link, page=1, page_size=20, highlights=True, detailed=True, request=None):
        aims_url = "https://api.aimsapi.com/v1/query/by-url"

        payload = {
            "link": link,
            "page": page,
            "page_size": page_size,
            "highlights": bool(highlights),
            "detailed": bool(detailed),
        }

        headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "X-Client-Id": settings.AIMS_CLIENT_ID,
            "X-Client-Secret": settings.AIMS_API_SECRET,
        }

        t0 = time.monotonic()
        logger.info("AIMS by-url request start page=%s link=%r", page, link)
        try:
            response = requests.post(
                aims_url,
                json=payload,
                headers=headers,
                timeout=(10, getattr(settings, "AIMS_REQUEST_TIMEOUT", 60)),
            )
        except requests.exceptions.Timeout:
            logger.warning("AIMS by-url request TIMEOUT after %.2fs", time.monotonic() - t0)
            return Response({"detail": "AIMS request timed out."}, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except requests.exceptions.RequestException as e:
            logger.exception("AIMS by-url request failed after %.2fs: %r", time.monotonic() - t0, e)
            return Response({"detail": "AIMS request failed."}, status=status.HTTP_502_BAD_GATEWAY)

        logger.info(
            "AIMS by-url response status=%s elapsed=%.2fs bytes=%s",
            response.status_code,
            time.monotonic() - t0,
            len(response.content) if response is not None else None,
        )

        try:
            aims_payload = response.json()
        except ValueError:
            logger.warning(
                "AIMS by-url invalid JSON status=%s text_preview=%r",
                response.status_code,
                (response.text or "")[:500],
            )
            return Response({"detail": "Invalid JSON received from AIMS."}, status=status.HTTP_502_BAD_GATEWAY)

        t1 = time.monotonic()
        debug_moods = bool(request and request.query_params.get("debug_moods") == "1")
        simplified = _simplify_aims_payload(aims_payload, debug_moods=debug_moods)
        logger.info("AIMS simplify elapsed=%.2fs results=%s", time.monotonic() - t1, simplified.get("count"))
        return Response(simplified, status=response.status_code)

    def _similarity_from_spotify(self, request, spotify_url: str):
        spotify_id = _extract_spotify_track_id(spotify_url)
        if not spotify_id:
            return Response({"detail": "spotify_url is not a valid spotify track url/uri"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sp = spotify_client()
            track_info = sp.track(spotify_id)
        except Exception:
            logger.exception("Spotify track lookup failed spotify_id=%r", spotify_id)
            return Response({"detail": "Spotify request failed"}, status=status.HTTP_502_BAD_GATEWAY)

        track_name = (track_info.get("name") or "").strip()
        artists = track_info.get("artists") or []
        artist_name = ((artists[0] or {}).get("name") if artists else None) or ""
        artist_names = [a.get("name") for a in artists if isinstance(a, dict) and a.get("name")]

        album = track_info.get("album") or {}
        images = album.get("images") or []
        image_url = ((images[0] or {}).get("url") if images else None) or None

        external_ids = track_info.get("external_ids") or {}
        isrc = (external_ids.get("isrc") or "").strip().upper() or None

        qs = Track.objects.select_related("artist").all()
        track_obj = qs.filter(spotify_id=spotify_id).first()
        if track_obj is None and isrc:
            track_obj = qs.filter(isrc=isrc).first()

        exists_in_db = bool(track_obj)

        page = request.data.get("page") or request.query_params.get("page") or 1
        page_size = request.data.get("page_size") or request.query_params.get("page_size") or 20
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(page_size)
        except (TypeError, ValueError):
            page_size = 20
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        aims_response = self._aims_query_by_url(
            link=spotify_url,
            page=page,
            page_size=page_size,
            highlights=True,
            detailed=True,
            request=request,
        )

        aims_data = aims_response.data if isinstance(aims_response.data, dict) else {"count": 0, "results": []}
        if "count" not in aims_data or "results" not in aims_data:
            aims_data = {"count": 0, "results": []}

        seed_track_payload = None
        if track_obj:
            seed_track_payload = _simplify_aims_item(
                {
                    "id_client": track_obj.aims_id,
                    "track_name": track_name,
                    "artist_canonical": artist_name,
                    "release_year": None,
                    "duration": None,
                }
            )
            if isinstance(seed_track_payload, dict):
                # Keep extra identifiers handy for the client.
                seed_track_payload["spotify_id"] = (track_obj.spotify_id or spotify_id) or None
                seed_track_payload["isrc"] = (track_obj.isrc or isrc) or None
                seed_track_payload["audience_sport_fit_percent"] = seed_track_payload.get("chartmetric_instagram_sports_fit_percent")

        response_payload = {
            "exists_in_db": exists_in_db,
            "track_uuid": getattr(track_obj, "uuid", None),
            "spotify": {
                "spotify_id": spotify_id,
                "isrc": isrc,
                "name": track_name,
                "artist": artist_name,
                "artists": artist_names,
                "image": image_url,
                "url": spotify_url,
            },
            # Keep backwards-compatible AIMS shape at the top-level.
            "count": aims_data.get("count") or 0,
            "results": aims_data.get("results") or [],
            # New: seed_track object to explicitly expose whether the seed is in our catalog.
            "seed_track": {
                "in_catalog": exists_in_db,
                "track": seed_track_payload,
            },
        }

        response_payload["aims_status_code"] = aims_response.status_code
        return Response(response_payload, status=aims_response.status_code)

    def create(self, request):
        # Handy for frontend dev/testing without calling AIMS.
        if request.query_params.get("dummy") == "1":
            return Response(DUMMY_SIMILARITY_RESPONSE, status=status.HTTP_200_OK)

        spotify_url = request.data.get("spotify_url") or request.query_params.get("spotify_url")
        if spotify_url:
            return self._similarity_from_spotify(request, spotify_url)

        youtube_url = request.data.get("youtube_url")
        page = request.data.get("page", 1)

        if not youtube_url:
            return Response(
                {"detail": "youtube_url is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if isinstance(youtube_url, str) and ("open.spotify.com/track/" in youtube_url or youtube_url.lower().startswith("spotify:track:")):
            return self._similarity_from_spotify(request, youtube_url)
        return self._aims_query_by_url(link=youtube_url, page=page, page_size=20, highlights=True, detailed=True, request=request)

    @action(detail=False, methods=["post"], url_path="spotify")
    def spotify(self, request):
        """
        Similarity search using a Spotify track URL/URI as seed.

        Always returns Spotify metadata (name, artist, image) and whether we have the track in our DB.
        If we can obtain an audio URL (internal file_wav/file_mp3 or Spotify preview_url), we also return AIMS similarity results.
        """
        if request.query_params.get("dummy") == "1":
            return Response(
                {
                    "exists_in_db": False,
                    "spotify": {"name": "Dummy Track", "artist": "Dummy Artist", "image": None},
                    "similarity": DUMMY_SIMILARITY_RESPONSE,
                },
                status=status.HTTP_200_OK,
            )

        spotify_url = request.data.get("spotify_url") or request.query_params.get("spotify_url")
        if not spotify_url:
            return Response({"detail": "spotify_url is required"}, status=status.HTTP_400_BAD_REQUEST)
        return self._similarity_from_spotify(request, spotify_url)


class SimilarityPromptViewSet(ViewSet):
    """
    Similarity search by free-text prompt.
    Proxies to AIMS: POST https://api.aimsapi.com/v1/query/by-text
    """

    def create(self, request):
        text = request.data.get("text") or request.query_params.get("text")
        if isinstance(text, str) and text.strip().lower() == "test":
            return Response(DUMMY_PROMPT_TEST_RESPONSE, status=status.HTTP_200_OK)

        # Handy for frontend dev/testing without calling AIMS.
        if request.query_params.get("dummy") == "1":
            return Response(DUMMY_SIMILARITY_RESPONSE, status=status.HTTP_200_OK)

        page = request.data.get("page", 1)
        page_size = request.data.get("page_size", 50)

        if not text:
            return Response({"detail": "text is required"}, status=status.HTTP_400_BAD_REQUEST)

        aims_url = "https://api.aimsapi.com/v1/query/by-text"
        payload = {
            "text": text,
            "page": page,
            "page_size": page_size,
        }

        headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "X-Client-Id": settings.AIMS_CLIENT_ID,
            "X-Client-Secret": settings.AIMS_API_SECRET,
        }

        response = requests.post(aims_url, json=payload, headers=headers, timeout=30)
        try:
            aims_payload = response.json()
        except ValueError:
            return Response(
                {"detail": "Invalid JSON received from AIMS."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        debug_moods = request.query_params.get("debug_moods") == "1"
        return Response(_simplify_aims_payload(aims_payload, debug_moods=debug_moods), status=response.status_code)


class SimilarityVideoViewSet(ViewSet):
    """
    Upload a video to AIMS and return the cache hash.

    Proxies to AIMS: POST https://api.aimsapi.com/v1/upload
    """

    parser_classes = (MultiPartParser, FormParser)

    def create(self, request):
        # Handy for frontend dev/testing without calling AIMS.
        if request.query_params.get("dummy") == "1":
            return Response(DUMMY_SIMILARITY_RESPONSE, status=status.HTTP_200_OK)

        video_file = request.FILES.get("video_file")
        # Don't default paging for /v1/search: AIMS can be strict about accepted fields.
        page = request.data.get("page")
        page_size = request.data.get("page_size")

        if not video_file:
            return Response({"detail": "video_file is required"}, status=status.HTTP_400_BAD_REQUEST)

        aims_upload_url = "https://api.aimsapi.com/v1/upload"

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "X-Client-Id": settings.AIMS_CLIENT_ID,
            "X-Client-Secret": settings.AIMS_API_SECRET,
        }

        # AIMS expects a multipart upload. Their docs commonly use `file` as the field name.
        files = {
            "file": (
                getattr(video_file, "name", "video"),
                video_file,
                getattr(video_file, "content_type", "application/octet-stream"),
            )
        }

        response = requests.post(aims_upload_url, headers=headers, files=files, timeout=(10, 120))
        try:
            aims_payload = response.json()
        except ValueError:
            return Response(
                {"detail": "Invalid JSON received from AIMS."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        video_hash = aims_payload.get("hash") if isinstance(aims_payload, dict) else None
        print("[aims] upload hash:", video_hash)

        if not video_hash:
            return Response(
                {"detail": "AIMS upload did not return a hash.", "aims": aims_payload},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        aims_search_url = "https://api.aimsapi.com/v1/search"
        # Follow AIMS documented schema: required `seeds` and optional paging.
        search_payload = {"seeds": [{"type": "video", "value": video_hash}]}

        search_headers = {
            **headers,
            "Content-Type": "application/json",
        }
        print("[aims] search payload:", search_payload)
        search_response = requests.post(
            aims_search_url,
            headers=search_headers,
            json=search_payload,
            timeout=60,
        )
        try:
            search_json = search_response.json()
        except ValueError:
            return Response(
                {"detail": "Invalid JSON received from AIMS search."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if search_response.status_code >= 400:
            # Bubble up the error details so the frontend/dev can adjust the payload quickly.
            print("[aims] search error:", search_response.status_code, search_json)
            return Response(
                {"detail": "AIMS search failed", "aims": search_json},
                status=search_response.status_code,
            )

        # Return the same simplified schema as the other similarity endpoints.
        debug_moods = request.query_params.get("debug_moods") == "1"
        return Response(_simplify_aims_payload(search_json, debug_moods=debug_moods), status=search_response.status_code)


class AimsDownloadUrlView(APIView):
    """
    Authenticated endpoint to mint a presigned S3 URL for downloading a track file.

    POST /api/v1/aims/download-url/
    Body: { key?: string; url?: string; filename: string }
    Response: { url: string }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AimsDownloadUrlInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = serializer.validated_data["key"]
        filename = serializer.validated_data["filename"]

        bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "") or ""
        if not bucket:
            return Response({"detail": "S3 bucket not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        expires = int(
            getattr(settings, "AIMS_DOWNLOAD_URL_EXPIRE_SECONDS", 0)
            or getattr(settings, "AWS_QUERYSTRING_EXPIRE", 0)
            or 3600
        )
        expires = max(60, min(expires, 3600 * 24))

        s3 = _s3_client()
        try:
            presigned = s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                    "ResponseContentDisposition": _build_content_disposition(filename),
                },
                ExpiresIn=expires,
            )
        except Exception:
            logger.exception("Failed to generate presigned download url for key=%r", key)
            return Response({"detail": "Could not generate download url."}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"url": str(presigned)}, status=status.HTTP_200_OK)
