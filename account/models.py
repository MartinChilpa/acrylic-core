from django.apps import apps
from django.db import models
from django.contrib.auth import get_user_model


class UserType(models.TextChoices):
        ARTIST = 'ARTIST', 'Artist'
        BUYER = 'BUYER', 'Buyer'


# Django auth base user extension
        
User = get_user_model()

# add type field
User.add_to_class('type', models.CharField(max_length=10, choices=UserType.choices, blank=True, null=True))

# add get_profile_model() method
def get_profile_model(self):
    """ artist.Artist / buyer.Buyer """
    if not self.type:
          return None
    app_name = self.type.lower()
    model_name = self.type.title()
    return apps.get_model(f'{app_name}:{model_name}')
User.add_to_class('get_profile_model', get_profile_model)

# add get_profile() method
@property
def get_profile(self):
      """  user.artist / user.buyer """
      return getattr(self, self.type.lower())
User.add_to_class('profile', get_profile)
