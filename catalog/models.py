from datetime import timedelta
import os
from django.conf import settings
from django.db import models
from django.db.models import Count
from django.db import transaction
from django.utils.text import slugify
from taggit.managers import TaggableManager
from taggit.models import Tag, TaggedItem

from common.models import BaseModel
from common.storage import public_storage
from spotify.tasks import load_spotify_id
from chartmetric.tasks import load_chartmetric_ids
from catalog.validators import validate_isrc
import logging

logger = logging.getLogger(__name__)


class Distributor(BaseModel):
    name = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    # whitelist
    whitelist_email = models.EmailField(blank=True)
    whitelist_send = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']
 
    def __str__(self):
        return self.name


class Genre(BaseModel):
    name = models.CharField(max_length=80)
    code = models.SlugField(max_length=80, unique=True)
    
    class Meta:
        ordering = ['name']
        indexes = BaseModel.Meta.indexes + [
            models.Index(fields=['name']),
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Generate slug from title if not present
        if not self.code:
            self.code = slugify(self.name)
        super(Genre, self).save(*args, **kwargs)


def get_upload_path(instance, filename):
    return f'tracks/{instance.uuid}/{filename}'

def get_label_audio_upload_path(instance, filename):
    """
    For label-ingested tracks we want deterministic S3 keys:
      tracks/<label_slug>/<artist_spotify_id>/<isrc>.<ext>

    This is opt-in via a transient instance attribute set by the upload endpoint:
      instance._upload_as_label = True
    """
    if getattr(instance, "_upload_as_label", False):
        label_slug = getattr(instance, "_label_slug", None)
        if not label_slug:
            label = getattr(getattr(instance, "artist", None), "label", None)
            label_slug = getattr(label, "slug", None) or getattr(instance, "_label_fallback", None)

        artist_spotify_id = getattr(instance, "_artist_spotify_id", None) or getattr(
            getattr(instance, "artist", None), "spotify_id", None
        )
        isrc = getattr(instance, "isrc", None)

        if label_slug and artist_spotify_id and isrc:
            ext = os.path.splitext(filename or "")[1].lower() or ".bin"
            return f"tracks/{label_slug}/{artist_spotify_id}/{str(isrc).upper()}{ext}"

    return get_upload_path(instance, filename)

def get_waveform_upload_path(instance, filename):
    # Keep waveform metadata next to the track's audio under the same S3 prefix.
    audio_name = None
    if getattr(instance, "file_wav", None) and getattr(instance.file_wav, "name", None):
        audio_name = instance.file_wav.name
    elif getattr(instance, "file_mp3", None) and getattr(instance.file_mp3, "name", None):
        audio_name = instance.file_mp3.name

    if isinstance(audio_name, str) and audio_name.startswith("tracks/"):
        prefix = os.path.dirname(audio_name)
        if prefix:
            return f"{prefix}/waveform.json"
    return f"tracks/{instance.uuid}/waveform.json"


class Price(BaseModel):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    max_artist_tracks = models.PositiveIntegerField('Max tracks/artist', default=0, help_text='Max tracks allowed per artist with this price. Use 0 for unlimited')
    default = models.BooleanField(default=False)
    active = models.BooleanField(default=False)
    order = models.PositiveBigIntegerField(default=0)

    class Meta:
        ordering = ['order']
        indexes = BaseModel.Meta.indexes + [
            models.Index(fields=['order']),
        ]

    def get_available_tracks(self, artist):
        if self.max_artist_tracks > 0:
            available_tracks = self.max_artist_tracks - artist.tracks.filter(price=self).count()
            return available_tracks if available_tracks > 0 else 0
        return 'unlimited'

    def __str__(self):
        return self.name


class TierPrice(BaseModel):
    """ Tier price either linked to a price o to a given track """
    price = models.ForeignKey('catalog.Price', related_name='tier_prices', on_delete=models.CASCADE)
    #track = models.ForeignKey()
    tier = models.ForeignKey('buyer.Tier', related_name='tier_prices', on_delete=models.PROTECT)
    single_use_price = models.DecimalField(max_digits=8, decimal_places=2)
    subscription_price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        indexes = BaseModel.Meta.indexes
        constraints = [
            models.UniqueConstraint(
                fields=['tier', 'price'], 
                name='unique_tier_price'
            )
        ]

    def __str__(self):
        return f'{self.price} - {self.tier}'


class Track(BaseModel):

    class AimsStatus(models.TextChoices):
        PENDING = 'pending', 'pending'
        PROCESSING = 'processing', 'processing'
        SUCCESS = 'success', 'success'
        FINISHED = 'finished', 'finished'

    class RecordType(models.TextChoices):
        STUDIO = 'STUDIO', 'Studio'

    class Language(models.TextChoices):
        EN = 'EN', 'English'
        ES = 'ES', 'Spanish'

    # example USEE10001993
    isrc = models.CharField('ISRC', max_length=12, validators=[validate_isrc])
    artist = models.ForeignKey('artist.Artist', related_name='tracks', on_delete=models.PROTECT)
    name = models.CharField(max_length=250, blank=True)
    duration = models.PositiveIntegerField(null=True, help_text='Duration in milliseconds')

    distributor = models.ForeignKey(Distributor, related_name='tracks', on_delete=models.SET_NULL, blank=True, null=True)
    other_distributor = models.CharField(max_length=100, blank=True)
    other_distributor_email = models.EmailField(max_length=100, blank=True)

    # total_uses
    #price
    released = models.DateField(blank=True, null=True)
    is_cover = models.BooleanField(default=False)
    is_remix = models.BooleanField(default=False)
    is_instrumental = models.BooleanField(default=False)
    is_explicit = models.BooleanField(default=False)
    
    #record_type = models.CharField(max_length=10, choices=RecordType.choices, default=RecordType.STUDIO)
    bpm = models.PositiveIntegerField('BPM', blank=True, null=True)
    language = models.CharField(max_length=2, choices=Language.choices, blank=True)
    lyrics = models.TextField(blank=True)

    # images
    cover_image = models.ImageField(upload_to=get_upload_path, storage=public_storage, blank=True)

    # aduio
    snippet  = models.FileField(upload_to=get_upload_path, blank=True)
    file_wav = models.FileField(upload_to=get_label_audio_upload_path, blank=True)
    file_mp3 = models.FileField(upload_to=get_upload_path, blank=True)
    waveform = models.FileField(upload_to=get_waveform_upload_path, blank=True)

    genres = models.ManyToManyField('catalog.Genre', related_name='tracks', blank=True)
    additional_main_artists = models.ManyToManyField('artist.Artist', blank=True, related_name='other_tracks_main')
    featured_artists = models.ManyToManyField('artist.Artist', blank=True, related_name='other_tracks_featured')

    tags = TaggableManager(blank=True)

    # cost
    price = models.ForeignKey(Price, related_name='tracks', blank=True, null=True, on_delete=models.SET_NULL)

    #moods
    #cultures
    #instruments
    #styles
    #season
    #similar_artists
    aims_id = models.PositiveBigIntegerField(blank=True, null=True, db_index=True)
    aims_status = models.CharField(
        max_length=20,
        choices=AimsStatus.choices,
        default=AimsStatus.PENDING,
        db_index=True,
    )


    # external ids
    spotify_id = models.CharField(max_length=30, blank=True)
    chartmetric_id = models.CharField(max_length=30, blank=True)

    # metrics
    spotify_popularity = models.PositiveIntegerField(default=0) # integer between 1 and 100
    virality = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['-id']
        indexes = BaseModel.Meta.indexes + [
            models.Index(fields=['isrc']),
            models.Index(fields=['spotify_id']),
            models.Index(fields=['chartmetric_id']),
        ]

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Used by background enrichment tasks (Spotify/Chartmetric) to avoid
        # triggering audio-processing side effects (AIMS upload, waveform).
        skip_audio_tasks = bool(kwargs.pop("skip_audio_tasks", False))

        # load external ids when object is created
        load_ids = True if not self.id else False
        super(Track, self).save(*args, **kwargs)

        # Ensure we always have a stable client id for AIMS correlation.
        # We use Track.id (autoincrement) as the consecutive numeric id.
        if self.id and self.aims_id is None:
            aims_id = int(self.id) + int(getattr(settings, "AIMS_ID_OFFSET", 0) or 0)
            type(self).objects.filter(pk=self.pk, aims_id__isnull=True).update(aims_id=aims_id)
            self.aims_id = aims_id

        if load_ids:
            try:
                # Enqueue after commit so workers can see the newly-created row.
                transaction.on_commit(lambda: load_spotify_id.delay(self.id, load_data=True))
                transaction.on_commit(lambda: load_chartmetric_ids.delay(self.id))
            except Exception:
                # Don't break the save flow if Celery/Redis isn't available.
                logger.exception("Failed to enqueue external-id tasks for track_id=%s", self.id)

        if not skip_audio_tasks:
            # Upload to AIMS once we have an audio file and haven't queued it yet.
            if self.id and (self.file_wav or self.file_mp3) and self.aims_status == self.AimsStatus.PENDING:
                updated = type(self).objects.filter(pk=self.pk, aims_status=self.AimsStatus.PENDING).update(
                    aims_status=self.AimsStatus.PROCESSING
                )
                if updated:
                    try:
                        from catalog.tasks import upload_track_to_aims
                        transaction.on_commit(lambda: upload_track_to_aims.delay(self.id))
                    except Exception:
                        # Avoid breaking the main save path if Celery isn't available.
                        logger.exception("Failed to enqueue AIMS upload for track_id=%s", self.id)

            # Generate waveform JSON when an audio file is present and waveform is missing.
            # Done async because it can be slow and may involve external storage.
            if self.id and (self.file_wav or self.file_mp3) and not self.waveform:
                try:
                    from catalog.tasks import generate_track_waveform
                    transaction.on_commit(lambda: generate_track_waveform.delay(self.id))
                except Exception:
                    # Avoid breaking the main save path if Celery isn't available.
                    pass

    def get_duration(self):
        if self.duration:
            return timedelta(milliseconds=self.duration)
        return None

    def get_duration_display(self):
        if self.duration:
            return str(self.get_duration()).split('.')[0].split(':', 1)[-1]
        return ''

    def get_latest_signed_splitsheet(self):
        return self.split_sheets.exclude(signed=None).order_by('-signed').first()

    def get_price(self, user, use_type):
        if not getattr(user, 'buyer'):
            raise Exception('User is not a buyer')
        if use_type not in ['single_use', 'subscription']:
            raise Exception('Unknown use_type')
        
        # get price for a given user
        if self.price:
            # custom price
            price = self.price
        else:
            # default price
            price = Price.objects.get(default=True)
        
        tier_price = price.tier_prices.get(tier=user.buyer.tier)
        amount = getattr(tier_price, f'{use_type}_price')
        return amount

    def get_spotify_url(self):
        if self.spotify_id:
            return f'https://open.spotify.com/track/{self.spotify_id}'
        return ''
    
    def get_chartmetric_url(self):
        if self.chartmetric_id:
            return f'https://app.chartmetric.com/track/{self.chartmetric_id}/about'
        return ''


def get_sync_upload_path(instance, filename):
    return f'syncs/{instance.uuid}/{filename}'


class SyncList(BaseModel):
    artist = models.ForeignKey('artist.Artist', related_name='synclists', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # images
    cover_image = models.ImageField(upload_to=get_sync_upload_path, storage=public_storage, blank=True)
    background_image = models.ImageField(upload_to=get_sync_upload_path, storage=public_storage, blank=True)

    order = models.PositiveIntegerField(default=0)
    pinned = models.BooleanField(default=True, help_text='Pinned in artist profile.')
    tracks = models.ManyToManyField('catalog.Track', through='catalog.SyncListTrack', related_name='synclists', blank=True)

    def get_genres(self):
        # return genres
        track_ids = self.tracks.values_list('id', flat=True)
        return Genre.objects.filter(tracks__in=track_ids)

    def get_tags(self):
        track_ids = self.tracks.values_list('id', flat=True)
        tagged_item_ids = TaggedItem.objects.filter(
            content_type__app_label='catalog',  # Use the correct app label
            content_type__model='track', # Model name must be lowercase
            object_id__in=track_ids
        ).values_list('id', flat=True)  # Retrieve only tag IDs to avoid unnecessary data
        return Tag.objects.filter(taggit_taggeditem_items__in=tagged_item_ids)

    def __str__(self):
        return self.name 

    class Meta:
        indexes = BaseModel.Meta.indexes + [
            models.Index(fields=['order']),
        ]


class SyncListTrack(models.Model):
    synclist = models.ForeignKey('catalog.SyncList', on_delete=models.CASCADE)
    track = models.ForeignKey('catalog.Track', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['synclist', 'order']),
        ]
