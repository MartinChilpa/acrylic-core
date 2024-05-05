from django.db import models
from common.models import BaseModel
from legal.validators import validate_percent


class SplitSheet(BaseModel):
    artist = models.ForeignKey('artist.Artist', related_name='split_sheets', on_delete=models.CASCADE) 
    track = models.ForeignKey('catalog.Track', related_name='split_sheets', on_delete=models.CASCADE, blank=True, null=True)
    # alternative for when no track is selected
    track_name = models.CharField(max_length=150, blank=True)
    
    # signature fields with Dropbox Sign
    signed = models.DateTimeField(blank=True, null=True, default=None)
    signature_request_id = models.CharField(max_length=50, blank=True)

    def __str__(self):
        if self.track:
            return self.track.name
        return self.track_name


class BaseSplitModel(BaseModel):
    name = models.CharField(max_length=250)
    legal_name = models.CharField(max_length=250, blank=True)
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
        return f'Publishing split for {self.track}'


class MasterSplit(BaseSplitModel):
    class Role(models.TextChoices):
        ARTIST = 'artist', 'Artist'
        PRODUCER = 'producer', 'Producer'
        LABEL = 'label', 'Record Label'
        OTHER = 'other', 'Other'

    split_sheet = models.ForeignKey(SplitSheet, related_name='master_splits', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ARTIST)

    def __str__(self):
        return f'Publishing split for {self.track}'
