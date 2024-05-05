from django.contrib import admin
from django.utils.html import format_html
from artist.models import Artist


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'name', 'country', 'chartmetric_id', 'spotify_id', 'spotify_followers', 'instagram_followers', 'created', 'updated', 'is_active', 'artist_links']
    search_fields = ['uuid', 'name', 'bio', 'spotify_url', 'spotify_id', 'chartmetric_id']
    list_filter= ['is_active', 'created', 'updated']
    raw_id_fields = ['user']

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
