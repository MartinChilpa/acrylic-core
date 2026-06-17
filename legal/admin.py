from django.contrib import admin
from django.utils.html import format_html
from legal.models import SplitSheet, PublishingSplit, MasterSplit, License, LicenseHistory


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


class LicenseHistoryInline(admin.TabularInline):
    model = LicenseHistory
    extra = 0
    can_delete = False
    readonly_fields = ["from_status", "to_status", "changed_by", "notes", "changed_at", "created", "updated", "uuid"]
    fields = readonly_fields
    ordering = ["-changed_at", "-created"]


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    inlines = [LicenseHistoryInline]
    list_display = ["uuid", "club", "track", "status_display", "starts_at", "ends_at", "currency", "price", "requested_by"]
    list_filter = ["status", "currency", "created", "updated", "starts_at", "ends_at"]
    search_fields = ["uuid", "club__club_name", "track__name", "track__isrc", "requested_by__email"]
    raw_id_fields = ["club", "track", "requested_by"]

    @admin.display(description="Status")
    def status_display(self, obj):
        return format_html(f'<span class="status {obj.status}">{obj.get_status_display()}</span>')


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
