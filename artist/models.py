from django.conf import settings
from django.db import models

from django_countries.fields import CountryField
from taggit.managers import TaggableManager

from common.models import BaseModel, ActiveManager
from catalog.validators import validate_isrc


class Artist(BaseModel):
    # user related to artist
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='artist', blank=True, null=True)
    name = models.CharField(max_length=250)
    bio = models.TextField(blank=True)
    hometown = models.CharField(max_length=250)
    country = CountryField(default='ES', blank_label='(seleccionar)')
    
    tags = TaggableManager()

    # external IDs
    chartmetric_id = models.CharField(max_length=100, blank=True)

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