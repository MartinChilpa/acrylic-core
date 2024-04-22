from django.db import models
from django.utils.text import slugify

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from taggit.managers import TaggableManager

from common.models import BaseModel
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


class Track(BaseModel):

    class RecordType(models.TextChoices):
        STUDIO = 'STUDIO', 'Studio'

    class Language(models.TextChoices):
        EN = 'EN', 'Enlgish'
        ES = 'ES', 'Spanish'

    # example USEE10001993
    isrc = models.CharField('ISRC', max_length=12, validators=[validate_isrc])
    artist = models.ForeignKey('artist.Artist', related_name='tracks', on_delete=models.PROTECT)
    name = models.CharField(max_length=250)
    duration = models.PositiveIntegerField(null=True) # in seconds / ms

    distributor = models.ForeignKey(Distributor, related_name='tracks', on_delete=models.SET_NULL, blank=True, null=True)

    # total_uses
    #price
    released = models.DateField(blank=True, null=True)
    is_cover = models.BooleanField(default=False)
    is_remix = models.BooleanField(default=False)
    is_instrumental = models.BooleanField(default=False)
    is_explicit = models.BooleanField(default=False)
    
    record_type = models.CharField(max_length=10, choices=RecordType.choices, default=RecordType.STUDIO)
    bpm = models.PositiveIntegerField('BPM', blank=True, null=True)
    language = models.CharField(max_length=2, choices=Language.choices, blank=True)
    lyrics = models.TextField(blank=True)

    # wav
    # mp3
    snippet  = models.FileField(upload_to=get_upload_path)
    file_wav = models.FileField(upload_to=get_upload_path)
    file_mp3 = models.FileField(upload_to=get_upload_path)

    genres = models.ManyToManyField('catalog.Genre', related_name='tracks', blank=True)
    additional_main_artists = models.ManyToManyField('artist.Artist', blank=True, related_name='other_tracks_main')
    featured_artists = models.ManyToManyField('artist.Artist', blank=True, related_name='other_tracks_featured')

    tags = TaggableManager(blank=True)
    #moods
    #cultures
    #instruments
    #styles
    #season
    #similar_artists

    #spotify_id (can be multiple....)
    
    class Meta:
        ordering = ['-id']
        indexes = [
            models.Index(fields=['isrc']),
        ]
    
    def __str__(self):
        return self.name
    
    def search_spotify_id(self):
        spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
        results = spotify.search(q=f'isrc:{self.isrc}', type='track', market='ES')
        return [t for t in results['tracks']['items'] if t['external_ids']['isrc'] == self.isrc]


class SyncList(BaseModel):
    artist = models.ForeignKey('artist.Artist', related_name='synclists', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    # cover
    order = models.PositiveIntegerField(default=0)
    pinned = models.BooleanField(default=True, help_text='Pinned in artist profile.')
    tracks = models.ManyToManyField('catalog.Track', through='catalog.SyncListTrack', related_name='synclists', blank=True)

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
