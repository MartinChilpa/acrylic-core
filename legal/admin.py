from django.contrib import admin
from django.utils.html import format_html
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
    list_display = ['uuid', 'artist', 'isrc', 'track', 'status_display', 'signed', 'signature_request_id']
    list_filter = ['status', 'signed', 'created', 'updated']
    search_fields = ['uuid', 'isrc', 'artist__name', 'track__name', 'signature_request_id']
    raw_id_fields = ['track', 'artist']

    @admin.display(description='Status')
    def status_display(self, obj):
        return format_html(f'<span class="status {obj.status}">{obj.get_status_display()}</span>')
