from django.contrib import admin
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from artist.models import Artist


class ArtistResource(resources.ModelResource):
    class Meta:
        model = Artist


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'name', 'country', 'kamrank', 'chartmetric_id', 'spotify_id', 'spotify_followers', 'instagram_followers', 'created', 'updated', 'is_active', 'artist_links']
    search_fields = ['uuid', 'name', 'bio', 'spotify_url', 'spotify_id', 'chartmetric_id']
    list_filter= ['is_active', 'created', 'updated']
    raw_id_fields = ['user']
    resource_classes = [ArtistResource]

    @admin.display(description='Links')
    def artist_links(self, obj):
        html = ''
        if obj.chartmetric_id:
            html += f'<a href="{obj.get_charmetric_url()}" target="_blank">CM</a> '
        if obj.spotify_url:
            html += f'<a href="{obj.spotify_url}" target="_blank">Spotify</a> '
        if obj.instagram_url:
            html += f'<a href="{obj.instagram_url}" target="_blank">IG</a>'
        return format_html(html)
