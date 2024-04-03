from django.db import models
from django.utils.text import slugify

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from taggit.managers import TaggableManager

from common.models import BaseModel
from catalog.validators import validate_isrc


class Genre(BaseModel):
    name = models.CharField(max_length=80)
    code = models.SlugField(max_length=80, unique=True)
    
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Generate slug from title if not present
        if not self.code:
            self.code = slugify(self.name)
        super(Genre, self).save(*args, **kwargs)


def get_upload_path(instance, filename):
    return f'tracks/{instance.project.uuid}/{filename}'


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
    # total_uses
    #price
    released = models.DateTimeField(blank=True, null=True)
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

    tags = TaggableManager()
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


def validate_percent(value, track_id=None):
    """
    Validator for the percent field to ensure all percents for a track sum up to a maximum of 100.00
    """
    # If track_id is not provided, try to extract it from the instance bound to the form
    # This is useful when the validator is used in forms where the track instance is bound
    if not track_id and 'instance' in locals():
        track_id = instance.track_id

    if track_id:
        # Calculate the total percent for the track excluding the current instance if updating
        total_percent = MasterSplit.objects.filter(track_id=track_id).exclude(id=instance.id).aggregate(models.Sum('percent'))['percent__sum'] or 0.0
        
        # Check if the total percent exceeds 100.00 when adding the new value
        if total_percent + value > 100.00:
            raise ValidationError('The total percent for all splits of a track cannot exceed 100.00.')



class PublishingSplit(BaseModel):
    track = models.ForeignKey('catalog.Track', related_name='publishing_splits', on_delete=models.CASCADE)
    owner_name = models.CharField(max_length=250, blank=True)
    owner_email = models.EmailField(blank=True)
    # owner = 
    percent = models.DecimalField(max_digits=5, decimal_places=2, validators=[validate_percent])
    #signed = 
    #dropbox_sign = 
    
    def __str__(self):
        return f'Publishing split for {self.track}'


class MasterSplit(BaseModel):
    track = models.ForeignKey('catalog.Track', related_name='master_splits', on_delete=models.CASCADE)
    owner_name = models.CharField(max_length=250, blank=True)
    owner_email = models.EmailField(blank=True)
    percent = models.DecimalField(max_digits=5, decimal_places=2)
    validated = models.DateTimeField(blank=True, null=True, default=None)

    def __str__(self):
        return f'Publishing split for {self.track}'

"""
class Price(BaseModel):
    track = 
"""