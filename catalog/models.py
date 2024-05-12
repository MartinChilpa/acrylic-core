from datetime import timedelta
from django.conf import settings
from django.db import models
from django.db.models import Count
from django.utils.text import slugify
from taggit.managers import TaggableManager
from taggit.models import Tag, TaggedItem

from common.models import BaseModel
from common.storage import public_storage
from spotify.tasks import load_spotify_id
from chartmetric.tasks import load_chartmetric_ids
from catalog.validators import validate_isrc


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
        indexes = [
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


class Price(BaseModel):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    single_use_price = models.DecimalField(max_digits=8, decimal_places=2)
    max_artist_tracks = models.PositiveIntegerField('Max tracks per artist', default=0, help_text='Use 0 for unlimited')
    default = models.BooleanField(default=False)
    active = models.BooleanField(default=False)
    order = models.PositiveBigIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['order']),
        ]

    def get_available_slots(self, artist):
        if self.max_artist_tracks > 0:
            return self.max_artist_tracks - artist.tracks.filter(price=self).count()
        return 'unlimited'

    def __str__(self):
        return self.name 


class Track(BaseModel):

    class RecordType(models.TextChoices):
        STUDIO = 'STUDIO', 'Studio'

    class Language(models.TextChoices):
        EN = 'EN', 'English'
        ES = 'ES', 'Spanish'

    # example USEE10001993
    isrc = models.CharField('ISRC', max_length=12, validators=[validate_isrc])
    artist = models.ForeignKey('artist.Artist', related_name='tracks', on_delete=models.PROTECT)
    name = models.CharField(max_length=250)
    duration = models.PositiveIntegerField(null=True, help_text='Duration in milliseconds')

    distributor = models.ForeignKey(Distributor, related_name='tracks', on_delete=models.SET_NULL, blank=True, null=True)

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
    file_wav = models.FileField(upload_to=get_upload_path, blank=True)
    file_mp3 = models.FileField(upload_to=get_upload_path, blank=True)

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

    # external ids
    spotify_id = models.CharField(max_length=30, blank=True)
    chartmetric_id = models.CharField(max_length=30, blank=True)

    # metrics
    spotify_popularity = models.PositiveIntegerField(default=0) # integer between 1 and 100

    class Meta:
        ordering = ['-id']
        indexes = [
            models.Index(fields=['isrc']),
            models.Index(fields=['spotify_id']),
            models.Index(fields=['chartmetric_id']),
        ]

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # load external ids when object is created
        load_ids = False if not self.id else True
        super(Track, self).save(*args, **kwargs)

        if load_ids:
            # async load spotify ids
            load_spotify_id.delay(self.id)
            # async task to load charmetric ids
            load_chartmetric_ids.delay(self.id)

    def get_duration(self):
        return timedelta(milliseconds=self.duration)

    def get_latest_signed_splitsheet(self):
        return self.split_sheets.exclude(signed=None).order_by('-signed').first()

    def get_price(self):
        return self.price or Price.objects.get(default=True)


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
        indexes = [
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
