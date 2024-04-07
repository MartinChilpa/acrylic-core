from django.db import models
from common.models import BaseModel
from legal.validators import validate_percent


class BaseSplitModel(BaseModel):
    track = models.ForeignKey('catalog.Track', related_name='publishing_splits', on_delete=models.CASCADE)
    owner_name = models.CharField(max_length=250, blank=True)
    owner_email = models.EmailField(blank=True)
    percent = models.DecimalField(max_digits=5, decimal_places=2)

    # signature fields with Dropbox Sign
    signature_request_id = models.CharField(max_length=50, blank=True)
    validated = models.DateTimeField(blank=True, null=True, default=None)

    class Meta:
        abstract = True


class PublishingSplit(BaseSplitModel):
    
    def __str__(self):
        return f'Publishing split for {self.track}'


class MasterSplit(BaseSplitModel):
    track = models.ForeignKey('catalog.Track', related_name='master_splits', on_delete=models.CASCADE)
    owner_name = models.CharField(max_length=250, blank=True)
    owner_email = models.EmailField(blank=True)
    percent = models.DecimalField(max_digits=5, decimal_places=2)

    

    def __str__(self):
        return f'Publishing split for {self.track}'