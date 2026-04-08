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
    class UserType(models.TextChoices):
        ARTIST = 'ARTIST', 'artist'
        CLUB = 'CLUB', 'club'
        LABEL = 'LABEL', 'label'
        UND = 'UND', 'und'
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='account', on_delete=models.PROTECT)
    user_type = models.CharField(max_length=20,choices=UserType.choices,default=UserType.ARTIST)
    billing_email = models.EmailField(blank=True)
    billing_details = models.TextField(blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    phone = models.PositiveIntegerField(null=True, blank=True)
    tax_id = models.CharField(max_length=20, blank=True)
    failed_payment_notifications = models.BooleanField(default=True)
    # contract signature
    contract_signed = models.DateTimeField(blank=True, null=True)


    def __str__(self):
        return self.user.email


def get_upload_path(instance, filename):
    return f'documents/{instance.uuid}/{filename}'


class Document(BaseModel):
    class Type(models.TextChoices):
        REVENUE_SHARE = 'REVENUE_SHARE', 'Revenue Share Agreement'
        CONTRACT = 'CONTRACT', 'Contract'
        TOS = 'TOS', 'Terms of Service'
        TAX = 'TAX', 'Tax'
        OTHER = 'OTHER', 'Other'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='documents', on_delete=models.PROTECT)
    
    name = models.CharField(max_length=200)
    document = models.FileField(upload_to=get_upload_path)
    signed_document = models.FileField(upload_to=get_upload_path, blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.OTHER)

    # digital signature provider
    signature_request_id = models.CharField(max_length=50, blank=True)
    signed = models.DateTimeField(blank=True, null=True, default=None)

    class Meta: # type: ignore
        indexes = BaseModel.Meta.indexes + [
            models.Index(fields=['signature_request_id']),
        ]
        ordering = ['-created']

    def __str__(self):
        return self.name


class Invitation(BaseModel):
    class Language(models.TextChoices):
        EN = 'en', 'English'
        ES = 'es', 'Español'
    email = models.EmailField(unique=True)
    joined = models.BooleanField(editable=False, default=False)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.EN)
    invited_by = models.ForeignKey('auth.User', related_name='invitations', blank=True, null=True, on_delete=models.PROTECT)

    def __str__(self):
        return self.email
