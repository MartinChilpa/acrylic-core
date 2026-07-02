from django.db import models
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

    # Financial snapshots (taken at creation time for historical accuracy)
    tier                    = models.CharField(max_length=20, blank=True)
    extended_commercial_use = models.BooleanField(default=False)
    price                   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency                = models.CharField(max_length=3, default='USD')
    ecu_unit                = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'License'
        verbose_name_plural = 'Licenses'
        constraints = [
            models.UniqueConstraint(fields=['club', 'track'], name='unique_license_club_track')
        ]
        ordering = ['-created']

    @property
    def revenue(self):
        return self.price + self.ecu_unit

    def __str__(self):
        return f"{self.club} — {self.track} ({self.status})"
