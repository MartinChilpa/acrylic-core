from django.conf import settings
from django.db import models
from uuid import uuid4


class AimsVideoMultipartUpload(models.Model):
    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        COMPLETED = "completed", "Completed"
        PROCESSING = "processing", "Processing"
        FINISHED = "finished", "Finished"
        FAILED = "failed", "Failed"
        ABORTED = "aborted", "Aborted"

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="aims_video_uploads")
    s3_key = models.CharField(max_length=1024)
    s3_upload_id = models.TextField()
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=127, default="application/octet-stream")
    size_bytes = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)
    aims_hash = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["uuid"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.filename} ({self.status})"
