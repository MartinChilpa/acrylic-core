from django.db import models
from django.utils import timezone

from common.models import BaseModel


class License(BaseModel):
    STATUS_PENDING  = 'pending' # Inprogress  
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING,  'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    club                    = models.ForeignKey('club.Club',    related_name='licenses', on_delete=models.CASCADE)
    track                   = models.ForeignKey('catalog.Track', related_name='licenses', on_delete=models.CASCADE)

    status                  = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    email_sent              = models.BooleanField(default=False)
    email_error             = models.TextField(blank=True)

    # A license only shows up in the club's Licenses tab once the track has been
    # downloaded, so creating it (whitelisting, emails) stays separate from listing it.
    downloaded              = models.BooleanField(default=False)
    downloaded_at           = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'License'
        verbose_name_plural = 'Licenses'
        constraints = [
            models.UniqueConstraint(fields=['club', 'track'], name='unique_license_club_track')
        ]
        ordering = ['-created']

    def __str__(self):
        return f"{self.club} — {self.track} ({self.status})"

    def mark_downloaded(self):
        """Flag the license as downloaded. Idempotent: keeps the first download time."""
        if self.downloaded:
            return False
        self.downloaded = True
        self.downloaded_at = timezone.now()
        self.save(update_fields=['downloaded', 'downloaded_at', 'updated'])
        return True
