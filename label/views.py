import csv
import io
import logging
import re

from django.db import transaction

from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from artist.models import Artist


logger = logging.getLogger(__name__)

_HYPERLINK_RE = re.compile(
    r"""^\s*=\s*(?:HIPERVINCULO|HYPERLINK)\(\s*"(?P<url>[^"]+)"\s*[,;]\s*"(?P<label>[^"]*)"\s*\)\s*$""",
    re.IGNORECASE,
)


def _parse_hyperlink_formula(value: str):
    if not isinstance(value, str):
        return None
    match = _HYPERLINK_RE.match(value)
    if not match:
        return None
    return {"url": match.group("url"), "label": match.group("label")}


def _sniff_dialect(sample: str):
    sniffer = csv.Sniffer()
    try:
        return sniffer.sniff(sample, delimiters=",;\t|")
    except Exception:
        # Default to a reasonable "CSV" guess.
        return csv.excel


def _pick_artist_column(headers):
    if not headers:
        return None
    normalized = {h: (h or "").strip().lower() for h in headers}
    candidates = (
        "artist",
        "artist_name",
        "artistname",
        "artist_canonical",
        "artist canonical",
        "artista",
        "nombre_artista",
        "nombre artista",
    )
    for want in candidates:
        for header, header_lc in normalized.items():
            if header_lc == want:
                return header
    return None


def _column_label_to_index(label: str):
    """
    Convert spreadsheet column labels (A, B, ..., Z, AA, AB, ...) to 0-based index.
    Returns None if not a valid label.
    """
    if not isinstance(label, str):
        return None
    s = label.strip().upper()
    if not s or any(ch < "A" or ch > "Z" for ch in s):
        return None
    out = 0
    for ch in s:
        out = out * 26 + (ord(ch) - ord("A") + 1)
    return out - 1


def _pick_spotify_column(headers, requested):
    """
    Pick the spotify-url column. Supports:
      - header name (exact match)
      - 1-based numeric index (e.g. "10")
      - spreadsheet column label (e.g. "J")
    """
    if not headers:
        return None
    if requested:
        # header exact
        if requested in headers:
            return requested
        # 1-based numeric index
        if isinstance(requested, str) and requested.strip().isdigit():
            idx = int(requested.strip()) - 1
            if 0 <= idx < len(headers):
                return headers[idx]
        # spreadsheet column label
        idx = _column_label_to_index(str(requested))
        if idx is not None and 0 <= idx < len(headers):
            return headers[idx]

    # default to column J (10th column)
    idx = _column_label_to_index("J")
    if idx is not None and idx < len(headers):
        return headers[idx]
    return None


_SPOTIFY_ARTIST_ID_RE = re.compile(r"/artist/(?P<id>[A-Za-z0-9]+)")
_SPOTIFY_ARTIST_URI_RE = re.compile(r"^spotify:artist:(?P<id>[A-Za-z0-9]+)$", re.IGNORECASE)


def _extract_spotify_artist_id(value):
    if not isinstance(value, str):
        return None
    v = value.strip()
    if not v:
        return None
    m = _SPOTIFY_ARTIST_URI_RE.match(v)
    if m:
        return m.group("id")
    # strip query params/fragments for URL matching
    v_no_q = v.split("?", 1)[0].split("#", 1)[0]
    m = _SPOTIFY_ARTIST_ID_RE.search(v_no_q)
    if m:
        return m.group("id")
    # last fallback: if caller passed raw id
    if re.fullmatch(r"[A-Za-z0-9]{10,40}", v):
        return v
    return None


class UploadCsvPreviewView(APIView):
    """
    Upload a CSV/TSV file and return a parsed preview.

    Expects multipart/form-data with a `file` field.
    """

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "file is required"}, status=status.HTTP_400_BAD_REQUEST)

        max_bytes = int(request.query_params.get("max_bytes", 2_000_000))  # 2MB default
        max_rows = int(request.query_params.get("max_rows", 50))
        has_header = request.query_params.get("header", "1") != "0"

        raw = uploaded.read(max_bytes + 1)
        truncated = len(raw) > max_bytes
        if truncated:
            raw = raw[:max_bytes]

        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")

        dialect = _sniff_dialect(text[:4096])
        reader = csv.reader(io.StringIO(text), dialect=dialect)

        rows = []
        links = []
        headers = None

        for i, row in enumerate(reader):
            if i == 0 and has_header:
                headers = [c.strip() or f"col_{idx+1}" for idx, c in enumerate(row)]
                continue

            if not row:
                continue

            if headers is None:
                headers = [f"col_{idx+1}" for idx in range(len(row))]

            row_obj = {}
            for idx, header in enumerate(headers):
                value = row[idx].strip() if idx < len(row) and isinstance(row[idx], str) else (row[idx] if idx < len(row) else "")
                link = _parse_hyperlink_formula(value) if isinstance(value, str) else None
                if link:
                    links.append({"row": len(rows) + 1, "column": header, **link})
                    value = link["url"]
                row_obj[header] = value

            rows.append(row_obj)
            if len(rows) >= max_rows:
                break

        requested_artist_column = request.query_params.get("artist_column")
        artist_column = requested_artist_column or _pick_artist_column(headers) or (headers[0] if headers else None)
        artist_names = []
        artist_seen = set()
        if artist_column:
            for row in rows:
                value = row.get(artist_column)
                if not isinstance(value, str):
                    continue
                name = value.strip()
                if not name or name in artist_seen:
                    continue
                artist_seen.add(name)
                artist_names.append(name)

        requested_spotify_column = request.query_params.get("spotify_column")
        spotify_column = _pick_spotify_column(headers, requested_spotify_column)
        artists_with_spotify = []
        if artist_column and spotify_column:
            seen = {}
            for row in rows:
                name_val = row.get(artist_column)
                if not isinstance(name_val, str):
                    continue
                name = name_val.strip()
                if not name:
                    continue
                spotify_val = row.get(spotify_column)
                spotify_url = spotify_val.strip() if isinstance(spotify_val, str) else None
                existing = seen.get(name)
                if existing is None:
                    seen[name] = spotify_url
                else:
                    # Prefer the first non-empty spotify_url we encounter.
                    if (not existing) and spotify_url:
                        seen[name] = spotify_url

            artists_with_spotify = [{"name": name, "spotify_url": url} for name, url in seen.items()]

        logger.info(
            "csv_preview filename=%r size=%s delimiter=%r header=%s headers=%s rows=%s links=%s truncated=%s",
            getattr(uploaded, "name", None),
            getattr(uploaded, "size", None),
            getattr(dialect, "delimiter", ","),
            has_header,
            len(headers or []),
            len(rows),
            len(links),
            truncated,
        )

        return Response(
            {
                "filename": getattr(uploaded, "name", None),
                "size": getattr(uploaded, "size", None),
                "dialect": {
                    "delimiter": getattr(dialect, "delimiter", ","),
                    "quotechar": getattr(dialect, "quotechar", '"'),
                },
                "header": has_header,
                "headers": headers or [],
                "rows": rows,
                "links": links,
                "artist_column": artist_column,
                "spotify_column": spotify_column,
                "artists": artist_names,
                "artists_with_spotify": artists_with_spotify,
                "truncated": truncated,
            },
            status=status.HTTP_200_OK,
        )


class SaveArtistsView(APIView):
    """
    Persist artists for the authenticated label user.

    Body:
      { "artists_with_spotify": [{"name": "...", "spotify_url": "..."}, ...] }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        label = getattr(request.user, "label", None)
        if label is None:
            return Response({"detail": "Label profile is required."}, status=status.HTTP_403_FORBIDDEN)

        payload = request.data or {}
        items = payload.get("artists_with_spotify")
        if not isinstance(items, list):
            return Response({"detail": "artists_with_spotify must be a list"}, status=status.HTTP_400_BAD_REQUEST)

        normalized = []
        errors = []
        seen = set()
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append({"index": idx, "detail": "item must be an object"})
                continue

            name = item.get("name")
            spotify_url = item.get("spotify_url")

            if not isinstance(name, str) or not name.strip():
                errors.append({"index": idx, "detail": "name is required"})
                continue
            name = name.strip()

            if not isinstance(spotify_url, str) or not spotify_url.strip():
                errors.append({"index": idx, "detail": "spotify_url is required"})
                continue
            spotify_url = spotify_url.strip()

            spotify_id = _extract_spotify_artist_id(spotify_url)
            if not spotify_id:
                errors.append({"index": idx, "detail": "spotify_url is not a valid spotify artist url/uri"})
                continue

            key = (spotify_id, name)
            if key in seen:
                continue
            seen.add(key)

            normalized.append({"name": name, "spotify_url": spotify_url, "spotify_id": spotify_id})

        if not normalized:
            return Response({"created": 0, "updated": 0, "errors": errors}, status=status.HTTP_200_OK)

        spotify_ids = [n["spotify_id"] for n in normalized]
        existing = {a.spotify_id: a for a in Artist.objects.filter(spotify_id__in=spotify_ids)}

        created = 0
        updated = 0

        with transaction.atomic():
            to_create = []
            for entry in normalized:
                spotify_id = entry["spotify_id"]
                artist = existing.get(spotify_id)
                if artist:
                    changed = False
                    if artist.label_id != label.id:
                        artist.label = label
                        changed = True
                    if entry["spotify_url"] and artist.spotify_url != entry["spotify_url"]:
                        artist.spotify_url = entry["spotify_url"]
                        changed = True
                    if entry["name"] and artist.name != entry["name"]:
                        artist.name = entry["name"]
                        changed = True
                    if changed:
                        artist.save(update_fields=["label", "spotify_url", "name", "updated"])
                        updated += 1
                    continue

                to_create.append(
                    Artist(
                        label=label,
                        name=entry["name"],
                        spotify_url=entry["spotify_url"],
                        spotify_id=entry["spotify_id"],
                    )
                )

            if to_create:
                Artist.objects.bulk_create(to_create)
                created = len(to_create)

        return Response(
            {
                "created": created,
                "updated": updated,
                "errors": errors,
            },
            status=status.HTTP_200_OK,
        )
