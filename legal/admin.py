from django.contrib import admin
from legal.models import PublishingSplit, MasterSplit


@admin.register(PublishingSplit)
class PublishingSplitAdmin(admin.ModelAdmin):
    list_display = ['track', 'owner_name', 'owner_email', 'percent']
    raw_id_fields = ['track']


@admin.register(MasterSplit)
class MasterSplitAdmin(admin.ModelAdmin):
    list_display = ['track', 'owner_name', 'owner_email', 'percent']
    raw_id_fields = ['track']

