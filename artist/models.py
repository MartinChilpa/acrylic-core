from django.conf import settings
from django.db import models

from django_countries.fields import CountryField
from taggit.managers import TaggableManager

from common.models import BaseModel
from catalog.validators import validate_isrc


class Artist(BaseModel):
    name = models.CharField(max_length=250)
    bio = models.TextField(blank=True)
    hometown = models.CharField(max_length=250)
    country = CountryField(default='ES', blank_label='(seleccionar)')
    spotify_url = models.URLField(null=True, blank=True)
    tags = TaggableManager()

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