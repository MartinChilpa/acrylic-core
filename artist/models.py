from django.conf import settings
from django.db import models

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
    bio = models.TextField(blank=True)
    hometown = models.CharField(max_length=250)
    country = CountryField(default='ES', blank_label='(seleccionar)')
    
    # images
    image = models.ImageField(upload_to=get_aritst_upload_path, storage=public_storage, blank=True)
    background_image = models.ImageField(upload_to=get_aritst_upload_path, storage=public_storage, blank=True)

    tags = TaggableManager(blank=True)

    # external IDs
    spotify_id = models.CharField(max_length=30, blank=True)
    chartmetric_id = models.CharField(max_length=30, blank=True)

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
        indexes = [
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name


# W19 W6 tax form

#class Documents(BaseModel):
#    models.GenericIPAddressField(_(""), protocol="both", unpack_ipv4=False)