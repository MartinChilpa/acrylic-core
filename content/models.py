from django.db import models
from common.models import BaseModel
from common.storage import public_storage


def get_sync_upload_path(instance, filename):
    return f'content/{instance.uuid}/{filename}'


class Article(BaseModel):
    title = models.CharField(max_length=250)
    summary = models.TextField(blank=True)
    image = models.ImageField(upload_to=get_sync_upload_path, storage=public_storage)
    link_text = models.CharField(max_length=250)
    url = models.URLField()
    order = models.PositiveIntegerField()
    published = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title
