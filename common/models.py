# python imports
import uuid
from decimal import Decimal

# django imports
from django.db import models
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.core.validators import MaxValueValidator, MinValueValidator


class PostgresIndex(models.Index):
    @cached_property
    def max_name_length(self):
        # standard limit for compatibility with non-postgres is 30
        # https://code.djangoproject.com/ticket/31881
        return 60


class BaseModel(models.Model):
    """
    Base model
    """
    uuid = models.UUIDField(default=uuid.uuid4,
                            editable=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        indexes = [
            PostgresIndex(fields=['uuid'], name='%(app_label)s_%(class)s_uuid_idx'),
            PostgresIndex(fields=['created'], name='%(app_label)s_%(class)s_created_idx'),
            PostgresIndex(fields=['updated'], name='%(app_label)s_%(class)s_updated_idx'),
        ]