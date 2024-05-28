from django.conf import settings
from django.db import models
from common.models import BaseModel


class Tier(BaseModel):
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=20)
    description = models.TextField()

    def __str__(self):
        return self.name


class Buyer(BaseModel):
    # user related to artist
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='buyer', blank=True, null=True)
    tier = models.ForeignKey('buyer.Tier', related_name='buyers', on_delete=models.PROTECT)

    def __str__(self):
        return str(self.user)
