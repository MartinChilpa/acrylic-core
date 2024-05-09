from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html
from catalog.models import Distributor, Genre, Price, Track, SyncList, SyncListTrack


@admin.register(Distributor)
class DistributorAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'name', 'contact_name', 'email', 'whitelist_send', 'whitelist_email', 'created', 'updated']
    search_fields = ['uuid', 'name']
    list_filter = ['whitelist_send', 'created', 'updated']


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'created', 'updated']
    search_fields = ['code', 'name']
    list_filter = ['created', 'updated']


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ['name', 'single_use_price', 'max_artist_tracks', 'default', 'active', 'order']


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    queryset = Track.objects.select_related('artist')
    list_display = ['isrc', 'name', 'artist_link', 'distributor', 'duration', 'released', 'is_cover', 
                    'is_remix', 'is_instrumental', 'is_explicit', 'created', 'updated']
    list_filter = ['released', 'distributor', 'is_remix', 'is_cover', 'is_instrumental', 'created', 'updated']
    search_fields = ['uuid', 'isrc', 'name', 'duration', 'artist__name']
    raw_id_fields = ['artist']
    filter_horizontal = ['genres', 'additional_main_artists', 'featured_artists']

    @admin.display(ordering='artist', description='Artist')
    def artist_link(self, obj):
        link = reverse('admin:artist_artist_change', args=[obj.artist_id])
        return format_html('<a href="{}">{}</a>', link, obj.artist.name)


class SyncListTrackInline(admin.TabularInline):
    model = SyncListTrack
    extra = 1
    fields = ['track', 'order']
    raw_id_fields = ['track']

@admin.register(SyncList)
class SyncListAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'name', 'artist', 'order', 'tracks_count', 'pinned', 'created', 'updated']
    list_filter = ['pinned', 'created', 'updated']
    search_fields = ['uuid', 'name', 'description', 'artist__name']
    raw_id_fields = ['artist']
    inlines = [SyncListTrackInline]

    def get_queryset(self, request):
        # Use 'annotate' to count the number of tracks for each SyncList
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(_tracks_count=Count('tracks'))
        return queryset

    def tracks_count(self, obj):
        # Use the annotated value for display
        return obj._tracks_count
    tracks_count.admin_order_field = '_tracks_count'
    tracks_count.short_description = 'Tracks'