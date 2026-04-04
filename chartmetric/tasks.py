import time
from django.apps import apps
from celery.utils.log import get_task_logger
from django.utils import timezone
from chartmetric.engine import Chartmetric
from acrylic.celery import app

logger = get_task_logger(__name__)

@app.task
def load_chartmetric_instagram_audience_stats(artist_id, since='2021-09-13', limit=3):
    """
    Loads Chartmetric Instagram audience stats and stores snapshots on Artist as JSON.

    Endpoints used:
    - artist/{id}/social-audience-stats statsType=country
    - artist/{id}/social-audience-stats statsType=city
    - artist/{id}/social-audience-stats statsType=demographic
    """
    Artist = apps.get_model('artist', 'Artist')

    try:
        artist = Artist.objects.get(id=artist_id)
    except Artist.DoesNotExist:
        logger.info("load_chartmetric_instagram_audience_stats: artist_id=%s NOT FOUND", artist_id)
        return False

    if not artist.chartmetric_id:
        return False

    cm = Chartmetric()
    cm.authenticate()

    # Chartmetric is strict about RPS; keep spacing between calls.
    updated_any = False

    time.sleep(1.5)
    countries_res = cm.get_social_audience_stats(
        artist.chartmetric_id,
        domain="instagram",
        audience_type="followers",
        stats_type="country",
        since=since,
        limit=limit,
    )
    if isinstance(countries_res, dict) and countries_res.get("error"):
        logger.warning(
            "load_chartmetric_instagram_audience_stats: countries error=%r artist_id=%s chartmetric_id=%r",
            countries_res.get("error"),
            artist_id,
            artist.chartmetric_id,
        )
    else:
        artist.chartmetric_instagram_top_countries = (countries_res or {}).get("obj") or []
        updated_any = True

    time.sleep(1.5)
    cities_res = cm.get_social_audience_stats(
        artist.chartmetric_id,
        domain="instagram",
        audience_type="followers",
        stats_type="city",
        since=since,
        limit=limit,
    )
    if isinstance(cities_res, dict) and cities_res.get("error"):
        logger.warning(
            "load_chartmetric_instagram_audience_stats: cities error=%r artist_id=%s chartmetric_id=%r",
            cities_res.get("error"),
            artist_id,
            artist.chartmetric_id,
        )
    else:
        artist.chartmetric_instagram_top_cities = (cities_res or {}).get("obj") or []
        updated_any = True

    time.sleep(1.5)
    demo_res = cm.get_social_audience_stats(
        artist.chartmetric_id,
        domain="instagram",
        audience_type="followers",
        stats_type="demographic",
        since=since,
        # demographic is usually a single object in a list; keep the payload small.
        limit=1,
    )
    if isinstance(demo_res, dict) and demo_res.get("error"):
        logger.warning(
            "load_chartmetric_instagram_audience_stats: demographic error=%r artist_id=%s chartmetric_id=%r",
            demo_res.get("error"),
            artist_id,
            artist.chartmetric_id,
        )
    else:
        artist.chartmetric_instagram_demographics = (demo_res or {}).get("obj") or []
        updated_any = True

    def _sports_fit_percent_from_interests(obj_list):
        targets = {
            "sports",
            "activewear",
            "fitness & yoga",
            "healthy lifestyle",
        }
        # Chartmetric can return multiple rows per interest across different timestamps.
        # We want a snapshot, so keep only the latest row per interest_name.
        latest_by_interest = {}
        for row in obj_list or []:
            if not isinstance(row, dict):
                continue
            name = (row.get("interest_name") or "").strip().lower()
            if not name or name not in targets:
                continue

            prev = latest_by_interest.get(name)
            if not prev:
                latest_by_interest[name] = row
                continue

            # "timestp" is typically YYYY-MM-DD and lexicographically comparable.
            prev_ts = str(prev.get("timestp") or "")
            cur_ts = str(row.get("timestp") or "")
            if cur_ts and (not prev_ts or cur_ts > prev_ts):
                latest_by_interest[name] = row

        total = 0.0
        for row in latest_by_interest.values():
            try:
                total += float(row.get("weight") or 0)
            except (TypeError, ValueError):
                continue
        return round(total * 100.0, 2)

    # Interests (used to compute sports fit %).
    time.sleep(1.5)
    interests_res = cm.get_social_audience_stats(
        artist.chartmetric_id,
        domain="instagram",
        audience_type="followers",
        stats_type="interest",
        since=since,
        # Fetch enough to include the interests we care about (usually appear in top set).
        limit=50,
    )
    if isinstance(interests_res, dict) and interests_res.get("error"):
        logger.warning(
            "load_chartmetric_instagram_audience_stats: interest error=%r artist_id=%s chartmetric_id=%r",
            interests_res.get("error"),
            artist_id,
            artist.chartmetric_id,
        )
    else:
        interests_obj = (interests_res or {}).get("obj") or []
        artist.chartmetric_instagram_sports_fit_percent = _sports_fit_percent_from_interests(interests_obj)
        updated_any = True

    # Only bump the timestamp if at least one request succeeded, and avoid overwriting
    # previous good snapshots with empty data when Chartmetric times out.
    if updated_any:
        artist.chartmetric_instagram_audience_updated_at = timezone.now()
        artist.save()

    logger.info("load_chartmetric_instagram_audience_stats: saved artist_id=%s", artist_id)
    return True


@app.task
def load_chartmetric_artist_ids(artist_id, force=False):
    # NOT USED!
    Artist = apps.get_model('artist', 'Artist')

    try:
        artist = Artist.objects.get(id=artist_id)
    except Artist.DoesNotExist:
        logger.info("load_chartmetric_artist_ids: artist_id=%s NOT FOUND", artist_id)
        return False
    else:
        if not (force is True or artist.chartmetric_id == ''):
            return True

        logger.info(
            "load_chartmetric_artist_ids: artist_id=%s force=%s current_chartmetric_id=%r",
            artist_id,
            force,
            artist.chartmetric_id,
        )

        # auth in chartmetric
        cm = Chartmetric()
        cm.authenticate()
        # chartmetric 1rps
        time.sleep(1.5)
        data = cm.get_artist_id_from_spotify(artist.name)
        if 'error' in data or not data.get('obj'):
            logger.warning(
                "load_chartmetric_artist_ids: Chartmetric error=%r has_obj=%s",
                data.get('error'),
                bool(data.get('obj')),
            )
            return False

        artists = (data.get('obj') or {}).get('artists') or []
        if not artists:
            return True

        artist_data = artists[0] or {}
        artist.chartmetric_id = artist_data.get('id') or ''
        artist.save()
        logger.info("load_chartmetric_artist_ids: saved chartmetric_id=%r artist_id=%s", artist.chartmetric_id, artist_id)
        return True
    return True


@app.task
def load_chartmetric_ids(track_id, force=False):

    Track = apps.get_model('catalog', 'track')

    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        logger.info("load_chartmetric_ids: track_id=%s NOT FOUND", track_id)
        return False

    if not (force is True or track.chartmetric_id == ''):
        return True

    logger.info(
        "load_chartmetric_ids: start track_id=%s isrc=%r force=%s current_chartmetric_id=%r",
        track_id,
        getattr(track, 'isrc', None),
        force,
        getattr(track, 'chartmetric_id', None),
    )

    cm = Chartmetric()
    cm.authenticate()
    time.sleep(1.5)
    data = cm.get_track_artist_ids_from_isrc(track.isrc)

    if 'error' in data or not data.get('obj'):
        logger.warning(
            "load_chartmetric_ids: Chartmetric error=%r has_obj=%s track_id=%s isrc=%r",
            data.get('error'),
            bool(data.get('obj')),
            track_id,
            track.isrc,
        )
        return False

    tracks = (data.get('obj') or {}).get('tracks') or []
    if not tracks:
        return True

    track_data = tracks[0] or {}
    cm_isrc = track_data.get('isrc')
    if cm_isrc != track.isrc:
        logger.info(
            "load_chartmetric_ids: ISRC mismatch (skip) chartmetric_isrc=%r local_isrc=%r track_id=%s",
            cm_isrc,
            track.isrc,
            track_id,
        )
        return True

    track.chartmetric_id = track_data.get('id') or ''
    artist = getattr(track, 'artist', None)
    track.save()
    logger.info("load_chartmetric_ids: saved track_id=%s chartmetric_id=%r", track_id, track.chartmetric_id)

    if artist is None:
        logger.warning("load_chartmetric_ids: track_id=%s has no artist relation", track_id)
        return True

    if not getattr(artist, 'chartmetric_id', ''):
        artist_ids = track_data.get('artist') or []
        artist.chartmetric_id = ((artist_ids[0] or {}).get('id') if artist_ids else None) or ''
        artist.save()
        logger.info("load_chartmetric_ids: saved artist_id=%s chartmetric_id=%r", artist.id, artist.chartmetric_id)
        load_chartmetric_stats.delay(artist.id)
        load_chartmetric_instagram_audience_stats.delay(artist.id)

    return True


@app.task
def load_chartmetric_stats(artist_id): 
    Artist = apps.get_model('artist', 'Artist')

    # auth in chartmetric
    cm = Chartmetric()
    cm.authenticate()

    # chartmetric 1rps
    time.sleep(1.5)
    
    try:
        artist = Artist.objects.get(id=artist_id)
    except Artist.DoesNotExist:
        logger.info("load_chartmetric_stats: artist_id=%s NOT FOUND", artist_id)
        return False

    if not artist.chartmetric_id:
        return False

    try:
        stats = cm.get_artist_stats(artist.chartmetric_id)
    except Exception:
        logger.exception("load_chartmetric_stats: exception fetching stats artist_id=%s", artist_id)
        return False

    spotify = stats.get('spotify') or {}
    instagram = stats.get('instagram') or {}
    tiktok = stats.get('tiktok') or {}
    youtube = stats.get('youtube_channel') or {}

    def _first_metric_value(obj, key, default=0):
 
        try:
            items = (obj or {}).get(key) or []
            first = next(iter(items), None) or {}
            return first.get('value') if first.get('value') is not None else default
        except Exception:
            return default


    # spotify URL
    if spotify.get('link'):
        artist.spotify_url = spotify['link']
    # spotify followers / popularity / listeners
    artist.spotify_followers = _first_metric_value(spotify, 'followers', default=0)
    artist.spotify_popularity = _first_metric_value(spotify, 'popularity', default=0)
    artist.spotify_monthly_listeners = _first_metric_value(spotify, 'listeners', default=0)

    # tiktok URL + followers/likes
    if tiktok.get('link'):
        artist.tiktok_url = tiktok['link']
    print("Tiktkp", _first_metric_value(tiktok, 'followers', default=0))
    artist.tiktok_followers = _first_metric_value(tiktok, 'followers', default=0)

    # instagram URL
    if instagram.get('link'):
        artist.instagram_url = instagram['link']
    # instagram followers
    artist.instagram_followers = _first_metric_value(instagram, 'followers', default=0)

    # youtube channel URL + subscribers
    if youtube.get('link'):
        artist.youtube_url = youtube['link']
    artist.youtube_followers = _first_metric_value(youtube, 'subscribers', default=0)


    artist.save()
    logger.info("load_chartmetric_stats: saved artist_id=%s", artist_id)

    return True
