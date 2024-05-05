from django.contrib import admin
from legal.models import SplitSheet, PublishingSplit, MasterSplit


class PublishingSplitInline(admin.TabularInline):
    model = PublishingSplit
    extra = 3
    exclude = []
    # fields = ['track', 'order']
    # raw_id_fields = ['track']

class MasterSplitInline(admin.TabularInline):
    model = MasterSplit
    extra = 3
    exclude = []


@admin.register(SplitSheet)
class SplitSheetAdmin(admin.ModelAdmin):
    inlines = [MasterSplitInline, PublishingSplitInline]
    list_display = ['uuid', 'track', 'track_name', 'signed', 'signature_request_id']
    list_filter = ['signed', 'created', 'updated']
    search_fields = ['uuid', 'track__name', 'track_name', 'signature_request_id']
    raw_id_fields = ['track']
