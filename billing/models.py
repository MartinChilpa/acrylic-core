from django.conf import settings
from django.db import models
from common.models import BaseModel


class Transaction(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='transactions', on_delete=models.PROTECT)