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
    billing_email = models.EmailField()
    billing_details = models.TextField(blank=True)
    country_code = models.PositiveIntegerField()
    phone = models.PositiveIntegerField()
    tax_id = models.CharField(max_length=20)
    failed_payment_notifications = models.BooleanField()

    def __str__(self):
        return self.user.email

#class Document(BaseModel):
#     name = 
#     document = 



     
#class Biiilng
#    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name)