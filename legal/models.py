from django.conf import settings
from django.db import models
from django.utils import timezone
from common.models import BaseModel
from common.storage import public_storage
from catalog.validators import validate_isrc
from legal.validators import validate_percent
from legal.tasks import request_signatures_task
from spotify.tasks import split_sheet_load_spotify_data_task
from club.models import Club
from catalog.models import Track


def get_upload_path(instance, filename):
    return f'split-sheets/{instance.uuid}/{filename}'


class SplitSheet(BaseModel):
    class Status(models.TextChoices):
        CREATED = 'CREATED', 'Created'
        PENDING = 'PENDING', 'Pending signature'
        SIGNED = 'SIGNED', 'Signed'
        EXPIRED = 'EXPIRED', 'Signature expired'

    artist = models.ForeignKey('artist.Artist', related_name='split_sheets', on_delete=models.CASCADE)
    track = models.OneToOneField('catalog.Track', related_name='split_sheet', on_delete=models.CASCADE, blank=True, null=True)
    isrc = models.CharField('ISRC', max_length=12, validators=[validate_isrc], blank=True)
    
    # alternative for when no track is selected
    track_name = models.CharField(max_length=150, blank=True)
    track_cover_image = models.ImageField(upload_to=get_upload_path, storage=public_storage, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    
    # digital signature provider
    signature_request_id = models.CharField(max_length=50, blank=True)
    signed = models.DateTimeField(blank=True, null=True, default=None)

    class Meta:
        indexes = BaseModel.Meta.indexes + [
            models.Index(fields=['signature_request_id']),
            models.Index(fields=['signed']),
            models.Index(fields=['status']),
            models.Index(fields=['isrc']),
        ]

    def __str__(self):
        if self.track:
            return self.track.name
        return self.track_name
    
    def save(self, *args, **kwargs):
        # load external ids when object is created
        load_track_data = True if not self.id else False
        super(SplitSheet, self).save(*args, **kwargs)

        if load_track_data:
            # async load spotify track name/cover
            split_sheet_load_spotify_data_task.delay(self.id)

    def request_signatures(self):
        request_signatures_task.delay(self.id)
        return True

    def get_isrc(self):
        if self.track:
            return self.track.irsc
        return self.isrc

    def get_track_name(self):
        if self.track:
            return self.track.name
        else:
            return self.track_name


class BaseSplitModel(BaseModel):
    name = models.CharField('full legal name', max_length=250)
    #legal_name = models.CharField(max_length=250, blank=True)
    email = models.EmailField()
    percent = models.DecimalField(max_digits=5, decimal_places=2)
    signed = models.DateTimeField(blank=True, null=True, default=None)

    class Meta:
        abstract = True


class PublishingSplit(BaseSplitModel):
    class Role(models.TextChoices):
        SONGWRITER = 'songwriter', 'Songwriter'
        COMPOSER = 'composer', 'Composer'
        PRODUCER = 'producer', 'Producer'
        LYRICIST = 'lyricist', 'Lyricist'
        REMIXER = 'remixer', 'Remixer'
        OTHER = 'other', 'Other'

    split_sheet = models.ForeignKey(SplitSheet, related_name='publishing_splits', on_delete=models.CASCADE)
    pro_name = models.CharField('PRO name', max_length=200, blank=True)
    ipi = models.PositiveIntegerField('IPI number', blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SONGWRITER)

    def __str__(self):
        return f'Publishing split for {self.split_sheet}'


class MasterSplit(BaseSplitModel):
    class Role(models.TextChoices):
        ARTIST = 'artist', 'Artist'
        PRODUCER = 'producer', 'Producer'
        LABEL = 'label', 'Record Label'
        OTHER = 'other', 'Other'

    split_sheet = models.ForeignKey(SplitSheet, related_name='master_splits', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ARTIST)

    def __str__(self):
        return f'Publishing split for {self.split_sheet}'


class License(BaseModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETE = "COMPLETE", "Complete"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    club = models.ForeignKey(Club, related_name="licenses", on_delete=models.PROTECT)
    track = models.ForeignKey(Track, related_name="licenses", on_delete=models.PROTECT)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="requested_licenses",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS, db_index=True)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(blank=True, null=True)
    currency = models.CharField(max_length=3, default="USD")
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created"]
        indexes = BaseModel.Meta.indexes + [
            models.Index(fields=["club", "status"]),
            models.Index(fields=["track", "status"]),
            models.Index(fields=["starts_at"]),
            models.Index(fields=["ends_at"]),
        ]

    def __str__(self):
        return f"{self.club} - {self.track} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        status_changed_by = kwargs.pop("status_changed_by", None)
        history_notes = kwargs.pop("history_notes", "")
        previous_status = None
        if self.pk:
            previous_status = type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()

        super().save(*args, **kwargs)

        if previous_status != self.status:
            LicenseHistory.objects.create(
                license=self,
                from_status=previous_status or "",
                to_status=self.status,
                changed_by=status_changed_by or self.requested_by,
                notes=history_notes or "",
            )


class LicenseHistory(BaseModel):
    license = models.ForeignKey(License, related_name="history", on_delete=models.CASCADE)
    from_status = models.CharField(max_length=20, blank=True, default="")
    to_status = models.CharField(max_length=20, choices=License.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="license_status_changes",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-changed_at", "-created"]
        indexes = BaseModel.Meta.indexes + [
            models.Index(fields=["license", "changed_at"]),
            models.Index(fields=["to_status"]),
        ]

    def __str__(self):
        return f"{self.license_id}: {self.from_status} -> {self.to_status}"
