from django.contrib import admin

from catalog.models import Genre, Track, PublishingSplit, MasterSplit


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'created', 'updated']
    search_fields = ['code', 'name']
    list_filter = ['created', 'updated']


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ['isrc', 'name', 'artist', 'duration', 'released', 'is_cover', 
                    'is_remix', 'is_instrumental', 'is_explicit', 'created', 'updated']
    list_filter = ['released', 'is_remix', 'is_cover', 'is_instrumental', 'created', 'updated']
    search_fields = ['name', 'duration', 'artist__name']
    raw_id_fields = ['artist']
    filter_horizontal = ['genres', 'additional_main_artists', 'featured_artists']


@admin.register(PublishingSplit)
class PublishingSplitAdmin(admin.ModelAdmin):
    list_display = ['track', 'owner_name', 'owner_email', 'percent']
    raw_id_fields = ['track']


@admin.register(MasterSplit)
class MasterSplitAdmin(admin.ModelAdmin):
    list_display = ['track', 'owner_name', 'owner_email', 'percent']
    raw_id_fields = ['track']

