import logging
import os
import shutil
import subprocess
import tempfile

from django.apps import apps
from django.core.files.base import ContentFile

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

