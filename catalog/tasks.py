import logging
import os
import shutil
import subprocess
import tempfile

import requests

from django.apps import apps
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone

from acrylic.celery import app


logger = logging.getLogger(__name__)

def _looks_like_wav(path):
    try:
        with open(path, "rb") as fp:
            head = fp.read(12)
        return len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == b"WAVE"
    except OSError:
        return False


@app.task
def generate_track_waveform(track_id, force=False, samples_per_pixel=1024, bits=8):
    """
    Generate an Audiowaveform-compatible JSON for Peaks.js and store it in Track.waveform.

    Requires the `audiowaveform` binary to be installed on the worker machine.
    """
    Track = apps.get_model("catalog", "Track")

    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        return False

    audio_field = track.file_wav if track.file_wav else track.file_mp3
    if not audio_field:
        return False

    if track.waveform and not force:
        return True

    audiowaveform_bin = shutil.which("audiowaveform")
    if not audiowaveform_bin:
        logger.error("audiowaveform binary not found; cannot generate waveform for track_id=%s", track_id)
        return False

    input_path = None
    wav_path = None
    output_path = None
    try:
        suffix = ".wav" if audio_field == track.file_wav else ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as input_fp:
            input_path = input_fp.name
            with audio_field.open("rb") as src:
                shutil.copyfileobj(src, input_fp)

        # Ensure we pass a real WAV to audiowaveform.
        if suffix == ".wav" and _looks_like_wav(input_path):
            wav_path = input_path
        else:
            ffmpeg_bin = shutil.which("ffmpeg")
            if not ffmpeg_bin:
                logger.error(
                    "ffmpeg binary not found; cannot decode audio for waveform track_id=%s",
                    track_id,
                )
                return False

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_fp:
                wav_path = wav_fp.name

            cmd = [
                ffmpeg_bin,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                input_path,
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "44100",
                "-ac",
                "1",
                wav_path,
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as output_fp:
            output_path = output_fp.name

        cmd = [
            audiowaveform_bin,
            "-i",
            wav_path,
            "-o",
            output_path,
            "-z",
            str(samples_per_pixel),
            "-b",
            str(bits),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        with open(output_path, "rb") as fp:
            data = fp.read()

        # upload_to ignores filename and will store under tracks/<uuid>/waveform.json
        track.waveform.save("waveform.json", ContentFile(data), save=False)
        track.save(update_fields=["waveform"])
        return True
    except subprocess.CalledProcessError as e:
        logger.error("audiowaveform failed for track_id=%s: %s", track_id, e.stderr or str(e))
        return False
    except Exception:
        logger.exception("waveform generation failed for track_id=%s", track_id)
        return False
    finally:
        for p in (input_path, wav_path, output_path):
            if p:
                try:
                    os.remove(p)
                except OSError:
                    pass


@app.task
def upload_track_to_aims(track_id, hook_url=None):
    """
    Upload a track audio file to AIMS so it can be used for similarity search later.

    POST https://api.aimsapi.com/v1/tracks
    multipart fields:
      - id_client: client-provided id (we use Track.aims_id, optionally prefixed per environment)
      - track: audio file (prefer WAV, fallback MP3)
      - track_name: track display name
      - release_year: integer year (Track.released.year or settings.AIMS_DEFAULT_RELEASE_YEAR)
      - hook_url: webhook callback URL
    """
    Track = apps.get_model("catalog", "Track")

    try:
        track = Track.objects.select_related("artist").get(id=track_id)
    except Track.DoesNotExist:
        return False

    if not track.aims_id:
        # We can't correlate AIMS results without a stable id_client.
        logger.warning("upload_track_to_aims: track_id=%s missing aims_id", track_id)
        return False

    audio_field = track.file_wav if track.file_wav else track.file_mp3
    if not audio_field:
        logger.warning("upload_track_to_aims: track_id=%s has no audio file (wav/mp3)", track_id)
        return False

    # Best-effort: snapshot Chartmetric virality at upload time.
    # Do not block AIMS upload if Chartmetric fails or isn't configured.
    if getattr(track, "chartmetric_id", ""):
        try:
            from chartmetric.engine import Chartmetric
            from chartmetric.dummy import DEFAULT_TRACK_VIRALITY

            cm = Chartmetric()
            if cm.authenticate():
                value = cm.get_track_virality(track.chartmetric_id)
                if not (isinstance(value, dict) and value.get("error")):
                    if value is None and bool(getattr(settings, "CHARTMETRIC_USE_DUMMY_FALLBACKS", False)):
                        value = DEFAULT_TRACK_VIRALITY
                    if value is not None:
                        Track.objects.filter(pk=track.pk).update(virality=value, updated=timezone.now())
                    logger.info(
                        "upload_track_to_aims: saved virality=%s track_id=%s chartmetric_id=%s",
                        value,
                        track_id,
                        track.chartmetric_id,
                    )
            else:
                logger.warning(
                    "upload_track_to_aims: Chartmetric auth failed; skipping virality track_id=%s chartmetric_id=%s",
                    track_id,
                    track.chartmetric_id,
                )
        except Exception:
            logger.exception("upload_track_to_aims: failed to fetch/save virality track_id=%s", track_id)
    else:
        logger.info("upload_track_to_aims: no chartmetric_id; skipping virality track_id=%s", track_id)

    aims_url = "https://api.aimsapi.com/v1/tracks"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "X-Client-Id": settings.AIMS_CLIENT_ID,
        "X-Client-Secret": settings.AIMS_API_SECRET,
    }

    hook_url = hook_url or getattr(settings, "AIMS_WEBHOOK_URL", "")
    release_year = None
    if getattr(track, "released", None):
        try:
            release_year = int(track.released.year)
        except Exception:
            release_year = None
    if release_year is None:
        release_year = int(getattr(settings, "AIMS_DEFAULT_RELEASE_YEAR", 2021) or 2021)

    data = {
        "id_client": str(track.aims_id),
        "track_name": track.name or "",
        "release_year": release_year,
        "hook_url": hook_url,
    }

    try:
        with audio_field.open("rb") as fp:
            files = {
                "track": (
                    os.path.basename(audio_field.name or "track"),
                    fp,
                    "application/octet-stream",
                )
            }
            resp = requests.post(aims_url, headers=headers, data=data, files=files, timeout=(10, 120))
    except requests.exceptions.RequestException as e:
        logger.exception("upload_track_to_aims: request failed track_id=%s: %r", track_id, e)
        # Let it be retried manually by resetting aims_status if needed.
        # Avoid Track.save() here to prevent an immediate re-enqueue loop.
        try:
            Track.objects.filter(pk=track.pk).update(
                aims_status=track.AimsStatus.PENDING,
                updated=timezone.now(),
            )
        except Exception:
            pass
        return False

    try:
        payload = resp.json()
    except ValueError:
        payload = {"error": "non_json_response", "status_code": resp.status_code, "text": (resp.text or "")[:500]}

    # If AIMS says the id_client already exists, treat it as success to avoid infinite retries.
    # This commonly happens when a previous upload succeeded but our system didn't persist SUCCESS.
    if resp.status_code == 422 and isinstance(payload, dict):
        id_client_errors = (payload.get("payload") or {}).get("id_client")
        if isinstance(id_client_errors, list) and any(
            "already" in str(msg).lower() and "taken" in str(msg).lower() for msg in id_client_errors
        ):
            logger.info(
                "upload_track_to_aims: id_client already exists; marking success track_id=%s aims_id_client=%s",
                track_id,
                track.aims_id,
            )
            try:
                Track.objects.filter(pk=track.pk).update(
                    aims_status=track.AimsStatus.FINISHED,
                    updated=timezone.now(),
                )
            except Exception:
                pass
            return True

    if resp.status_code >= 400:
        logger.warning("upload_track_to_aims: aims error track_id=%s status=%s payload=%s", track_id, resp.status_code, payload)
        # Reset to pending so we can retry later.
        #
        # IMPORTANT: do not call Track.save() here. Track.save() auto-enqueues an AIMS upload
        # when aims_status == PENDING, which can create a tight retry loop on any 4xx/5xx.
        try:
            Track.objects.filter(pk=track.pk).update(
                aims_status=track.AimsStatus.PENDING,
                updated=timezone.now(),
            )
        except Exception:
            pass
        return False

    logger.info(
        "upload_track_to_aims: uploaded track_id=%s aims_id_client=%s hook_url=%r",
        track_id,
        track.aims_id,
        hook_url,
    )
    # Keep it in PROCESSING until webhook confirms completion.
    try:
        Track.objects.filter(pk=track.pk).update(
            aims_status=track.AimsStatus.PROCESSING,
            updated=timezone.now(),
        )
    except Exception:
        pass
    return True
