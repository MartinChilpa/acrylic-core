from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from sorl.thumbnail import get_thumbnail
from spotify.tasks import load_spotify_id, load_spotify_track_data
from chartmetric.tasks import load_chartmetric_ids
from catalog.models import Distributor, Genre, Price, TierPrice, Track, SyncList, SyncListTrack
from buyer.models import Tier

# import/export resources
class TrackResource(resources.ModelResource):
    class Meta:
        model = Track


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


class TierPriceInline(admin.TabularInline):
    _tiers = 0

    model = TierPrice
    fields = ['tier', 'single_use_price', 'subscription_price']

    extra = 0  # Set to 0 initially, will be determined dynamically
    max_num = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tiers = Tier.objects.all()

    def get_extra(self, request, obj=None, **kwargs):
        return len(self._tiers)

    def get_max_num(self, request, obj=None, **kwargs):
        return len(self._tiers)

    def get_formset(self, request, obj=None, **kwargs):
        FormSet = super().get_formset(request, obj, **kwargs)
        default_values = [{'tier': tier} for tier in self._tiers]

        class CustomFormSet(FormSet):
            def __init__(self, *args, **kwargs):
                kwargs['initial'] = default_values
                super().__init__(*args, **kwargs)
        
        return CustomFormSet

@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ['name', 'max_artist_tracks', 'default', 'active', 'order']
    inlines = [TierPriceInline]


@admin.register(TierPrice)
class TierPriceAdmin(admin.ModelAdmin):
    list_display = ['price', 'tier', 'single_use_price', 'subscription_price', 'created', 'updated']
    list_filter = ['tier', 'price', 'created', 'updated']
    search_fields = ['price__name', 'tier__name', 'tier__code']


def reload_spotify_ids(modeladmin, request, queryset):
    for track in queryset:
        load_spotify_id.delay(track.id)
reload_spotify_ids.short_description = 'Reload Spotify IDs'


def reload_spotify_data(modeladmin, request, queryset):
    for track in queryset:
        load_spotify_track_data.delay(track.id)
reload_spotify_data.short_description = 'Reload Spotify cover image / 30s snippet'


def reload_chartmetric_ids(modeladmin, request, queryset):
    for track in queryset:
        load_chartmetric_ids.delay(track.id)
reload_chartmetric_ids.short_description = 'Reload IDs from Chartmetric'


@admin.register(Track)
class TrackAdmin(ImportExportModelAdmin):
    queryset = Track.objects.select_related('artist', 'distributor')
    list_display = ['isrc', 'cover_preview', 'name', 'artist_link', 'distributor', 'duration_display', 'released', 'snippet_preview',
                    'is_remix', 'is_instrumental', 'is_explicit', 'created', 'updated']
    list_filter = ['released', 'distributor', 'is_remix', 'is_instrumental', 'created', 'updated']
    search_fields = ['uuid', 'isrc', 'name', 'artist__name']
    raw_id_fields = ['artist']
    filter_horizontal = ['genres', 'additional_main_artists', 'featured_artists']
    resource_classes = [TrackResource]
    actions = [reload_spotify_ids, reload_spotify_data, reload_chartmetric_ids]
    change_list_template = 'admin/catalog/track/change_list.html'

    @admin.display(ordering='artist', description='Artist')
    def artist_link(self, obj):
        link = reverse('admin:artist_artist_change', args=[obj.artist_id])
        return format_html(f'<a href="{link}">{obj.artist.name}</a>')

    @admin.display(ordering='duration', description='Duration')
    def duration_display(self, obj):
        return obj.get_duration_display()

    @admin.display(ordering='snippet', description='Preview')
    def snippet_preview(self, obj):
        if obj.snippet:
            return format_html(f'<a href="#" class="play" data-url="{obj.snippet.url}">Play</a>')
        return ''
    
    @admin.display(ordering='cover_image', description='Cover')
    def cover_preview(self, obj):
        if obj.cover_image:
            thumbnail = get_thumbnail(obj.cover_image, '100x100', crop='center', quality=99)
            return format_html(f'<img src="{thumbnail.url}" class="cover">')
        return ''


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
