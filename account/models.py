from django.apps import apps
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from common.models import BaseModel


# Django auth base user extension        
User = get_user_model()
#User.add_to_class('username', None)
#setattr(User, 'username', None)
#setattr(User, 'email', None)
#models.EmailField(unique=True).contribute_to_class(User, 'email')
# User.add_to_class('USERNAME_FIELD', 'email')
# User.add_to_class('REQUIRED_FIELDS', [])

# add type field
#User.add_to_class('type', models.CharField(max_length=10, choices=UserType.choices, blank=True, null=True)


# add get_profile() method
"""
@property
def get_profile(self):
      #  user.artist / user.buyer
      artist = getattr(user, 'artist', None)
      if artist:
            return artist
      return getattr(user, 'buyer', None)
User.add_to_class('profile', get_profile)
"""

class Account(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='account', on_delete=models.PROTECT)
    billing_email = models.EmailField(blank=True)
    billing_details = models.TextField(blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    phone = models.PositiveIntegerField(null=True, blank=True)
    tax_id = models.CharField(max_length=20, blank=True)
    failed_payment_notifications = models.BooleanField(default=True)

    def __str__(self):
        return self.user.email


def get_upload_path(instance, filename):
    return f'documents/{instance.uuid}/{filename}'


class Document(BaseModel):
    class Type(models.TextChoices):
        REVENUE_SHARE = 'REVENUE_SHARE', 'Revenue Share Agreement'
        TOS = 'TOS', 'Terms of Service'
        TAX = 'TAX', 'Tax'
        OTHER = 'OTHER', 'Other'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='documents', on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    document = models.FileField(upload_to=get_upload_path)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.OTHER)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.name


class Invitation(BaseModel):
    email = models.EmailField(unique=True)
    joined = models.BooleanField(editable=False, default=False)

    def __str__(self):
        return self.email



