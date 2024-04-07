from django.contrib import admin

from artist.models import Artist


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ['name', 'created', 'updated']
    search_fields = ['name']
    list_filter= ['created', 'updated', 'country']
    raw_id_fields = ['user']

