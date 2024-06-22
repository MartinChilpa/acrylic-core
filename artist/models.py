from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from django_countries.fields import CountryField
from taggit.managers import TaggableManager

from common.storage import public_storage
from common.models import BaseModel, ActiveManager
from catalog.validators import validate_isrc


def get_aritst_upload_path(instance, filename):
    return f'syncs/{instance.uuid}/{filename}'


class Artist(BaseModel):
    # user related to artist
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='artist', blank=True, null=True)
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=100, blank=True) # slug for artist URL
    isni = models.CharField('ISNI', max_length=16, blank=True) # ISNI ISO format
    bio = models.TextField(blank=True)
    hometown = models.CharField(max_length=250, blank=True)
    country = CountryField(default='ES', blank_label='(seleccionar)')

    # images
    image = models.ImageField(upload_to=get_aritst_upload_path, storage=public_storage, blank=True)
    background_image = models.ImageField(upload_to=get_aritst_upload_path, storage=public_storage, blank=True)

    tags = TaggableManager(blank=True)

    # external IDs
    spotify_id = models.CharField(max_length=30, blank=True)
    chartmetric_id = models.CharField(max_length=30, blank=True)
    hubspot_id = models.CharField(max_length=30, blank=True)

    # social
    spotify_url = models.URLField(null=True, blank=True)
    tiktok_url = models.URLField(null=True, blank=True)
    twitter_url = models.URLField(null=True, blank=True)
    youtube_url = models.URLField(null=True, blank=True)
    twitch_url = models.URLField(null=True, blank=True)
    facebook_url = models.URLField(null=True, blank=True)
    shazam_url = models.URLField(null=True, blank=True)
    soundcloud_url = models.URLField(null=True, blank=True)
    pandora_url = models.URLField(null=True, blank=True)
    instagram_url = models.URLField(null=True, blank=True)
    itunes_url = models.URLField(null=True, blank=True)
    amazonmusic_url = models.URLField(null=True, blank=True)
    deezer_url = models.URLField(null=True, blank=True)

    # ranking
    kamrank = models.PositiveBigIntegerField('KAMRank', editable=False, null=True)

    # stats
    spotify_followers = models.PositiveIntegerField(default=0, editable=False)
    spotify_popularity = models.PositiveIntegerField(default=0, editable=False)
    spotify_monthly_listeners = models.PositiveIntegerField(default=0, editable=False)

    instagram_followers = models.PositiveIntegerField(default=0, editable=False)

    tiktok_followers = models.PositiveIntegerField(default=0, editable=False)
    tiktok_likes = models.PositiveIntegerField(default=0, editable=False)
    
    # youtube_subscribers = models.PositiveIntegerField(default=0) 
    # soundcloud_followers = models.PositiveIntegerField(default=0) 
    # youtube_monthly_video_views = models.PositiveIntegerField(default=0) 

    # active
    is_active = models.BooleanField(default=True)

    # managers
    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        ordering = ['-name']
        indexes = BaseModel.Meta.indexes + [
            models.Index(fields=['name']),
            models.Index(fields=['isni']),
            models.Index(fields=['spotify_id']),
            models.Index(fields=['chartmetric_id']),
            models.Index(fields=['-spotify_followers']),
            models.Index(fields=['-instagram_followers']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['slug'], 
                name='unique_slug',
                condition=~Q(slug='')
            )
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Generate slug if not present
        if self.slug:
            slug = slugify(self.name)
            same_slug_artists = Artist.objects.filter(slug=slug).exclude(id=self.id).count()
            if same_slug_artists > 0:
                slug = f'{slug}{same_slug_artists+1}'
            self.slug = slug
        super(Artist, self).save(*args, **kwargs)

    def get_charmetric_url(self):
        if self.chartmetric_id:
            return f'https://app.chartmetric.com/artist/{self.chartmetric_id}'
        return ''
    
    def get_spotify_url(self):
        if self.spotify_id:
            return f'https://open.spotify.com/artist/{self.spotify_id}'
        return ''

    def get_hubspot_url(self):
        if self.hubspot_id:
            return f'https://app.hubspot.com/contacts/{settings.HUBSPOT_PORTAL_ID}/contact/{self.hubspot_id}/'
        return ''

    def get_public_url(self):
        return f'{settings.ARTIST_PROFILE_BASE_URL}{self.slug}/'
