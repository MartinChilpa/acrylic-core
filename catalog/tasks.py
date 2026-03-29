import logging
import os
import shutil
import subprocess
import tempfile

import requests

from django.apps import apps
from django.core.files.base import ContentFile
from django.conf import settings

from acrylic.celery import app


logger = logging.getLogger(__name__)


@app.task
def generate_track_waveform(track_id, force=False, samples_per_pixel=256, bits=8):
    """
    Generate an Audiowaveform-compatible JSON for Peaks.js and store it in Track.waveform.

    Requires the `audiowaveform` binary to be installed on the worker machine.
    """
    Track = apps.get_model("catalog", "Track")

    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        return False

    if not track.file_wav:
        return False

    if track.waveform and not force:
        return True

    audiowaveform_bin = shutil.which("audiowaveform")
    if not audiowaveform_bin:
        logger.error("audiowaveform binary not found; cannot generate waveform for track_id=%s", track_id)
        return False

    input_path = None
    output_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as input_fp:
            input_path = input_fp.name
            # Copy remote/local storage file into a local temp file.
            with track.file_wav.open("rb") as src:
                shutil.copyfileobj(src, input_fp)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as output_fp:
            output_path = output_fp.name

        cmd = [
            audiowaveform_bin,
            "-i",
            input_path,
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
        for p in (input_path, output_path):
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
      - id_client: client-provided numeric id (we use Track.aims_id)
      - track: audio file (prefer WAV, fallback MP3)
      - track_name: track display name
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

    aims_url = "https://api.aimsapi.com/v1/tracks"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "X-Client-Id": settings.AIMS_CLIENT_ID,
        "X-Client-Secret": settings.AIMS_API_SECRET,
    }

    hook_url = hook_url or getattr(settings, "AIMS_WEBHOOK_URL", "")
    data = {
        "id_client": str(track.aims_id),
        "track_name": track.name or "",
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
        return False

    try:
        payload = resp.json()
    except ValueError:
        payload = {"error": "non_json_response", "status_code": resp.status_code, "text": (resp.text or "")[:500]}

    if resp.status_code >= 400:
        logger.warning("upload_track_to_aims: aims error track_id=%s status=%s payload=%s", track_id, resp.status_code, payload)
        # Reset to pending so we can retry later.
        try:
            track.aims_status = track.AimsStatus.PENDING
            track.save(update_fields=["aims_status"])
        except Exception:
            pass
        return False

    logger.info("upload_track_to_aims: uploaded track_id=%s aims_id_client=%s", track_id, track.aims_id)
    try:
        track.aims_status = track.AimsStatus.SUCCESS
        track.save(update_fields=["aims_status"])
    except Exception:
        pass
    return True
