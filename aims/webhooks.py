import logging

from django.apps import apps
from django.conf import settings
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


logger = logging.getLogger(__name__)


_SUCCESS_STATES = {"finished", "finish", "done", "completed", "complete", "success", "succeeded", "ok"}
_FAIL_STATES = {"failed", "failure", "error", "errored"}


def _extract_id_client(payload: dict):
    for key in ("id_client", "idClient", "id"):
        value = payload.get(key)
        if value is not None:
            return value
    nested = payload.get("payload")
    if isinstance(nested, dict):
        return _extract_id_client(nested)
    return None


def _extract_status_text(payload: dict) -> str:
    for key in ("status", "state", "event", "result"):
        value = payload.get(key)
        if value is not None:
            return str(value)
    nested = payload.get("payload")
    if isinstance(nested, dict):
        return _extract_status_text(nested)
    return ""


class AimsWebhookView(APIView):
    """
    AIMS webhook callback.

    Expects a payload that includes an `id_client` matching `Track.aims_id`.
    On success, marks `Track.aims_status` as `finished`.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        expected_secret = getattr(settings, "AIMS_WEBHOOK_SECRET", "") or ""
        if expected_secret:
            provided = (
                request.headers.get("X-Aims-Webhook-Secret")
                or request.headers.get("X-AIMS-WEBHOOK-SECRET")
                or request.query_params.get("secret")
            )
            if provided != expected_secret:
                return Response({"detail": "unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        payload = request.data if isinstance(request.data, dict) else {}
        id_client = _extract_id_client(payload)
        status_text = _extract_status_text(payload).strip().lower()
        success_flag = payload.get("success")
        ok_flag = payload.get("ok")

        Track = apps.get_model("catalog", "Track")

        if id_client is None:
            logger.warning("aims_webhook: missing id_client payload=%s", payload)
            return Response({"detail": "missing id_client"}, status=status.HTTP_200_OK)

        id_client_str = str(id_client).strip()
        if id_client_str.isdigit():
            aims_id = int(id_client_str)
        else:
            logger.warning("aims_webhook: non-numeric id_client=%r payload=%s", id_client_str, payload)
            return Response({"detail": "invalid id_client"}, status=status.HTTP_200_OK)

        is_success = False
        if success_flag is True or ok_flag is True:
            is_success = True
        elif status_text in _SUCCESS_STATES:
            is_success = True
        elif status_text in _FAIL_STATES:
            is_success = False

        if is_success:
            updated = Track.objects.filter(aims_id=aims_id).update(
                aims_status=Track.AimsStatus.FINISHED,
                updated=timezone.now(),
            )
            logger.info("aims_webhook: finished aims_id=%s updated=%s status_text=%r", aims_id, updated, status_text)
            return Response({"updated": updated, "aims_id": aims_id, "aims_status": "finished"}, status=status.HTTP_200_OK)

        logger.info("aims_webhook: received non-success aims_id=%s status_text=%r payload=%s", aims_id, status_text, payload)
        return Response({"updated": 0, "aims_id": aims_id, "aims_status": "ignored"}, status=status.HTTP_200_OK)

