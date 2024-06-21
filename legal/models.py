from django.db import models
from common.models import BaseModel
from common.storage import public_storage
from catalog.validators import validate_isrc
from legal.validators import validate_percent
from legal.tasks import request_signatures_task
from spotify.tasks import split_sheet_load_spotify_data_task


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
