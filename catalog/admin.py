from django.contrib import admin

from catalog.models import Genre, Track


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
