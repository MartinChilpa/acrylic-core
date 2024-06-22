from django.contrib import admin
from django.shortcuts import render, get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from artist.models import Artist


class ArtistResource(resources.ModelResource):
    class Meta:
        model = Artist


@admin.register(Artist)
class ArtistAdmin(ImportExportModelAdmin):
    list_display = ['view_object_link', 'name', 'country', 'kamrank', 'chartmetric_id', 'spotify_id', 'spotify_followers', 'instagram_followers', 'created', 'updated', 'is_active', 'artist_hubspot_link', 'artist_links']
    search_fields = ['uuid', 'name', 'bio', 'spotify_url', 'spotify_id', 'chartmetric_id', 'hubspot_id']
    list_filter= ['is_active', 'created', 'updated']
    raw_id_fields = ['user']
    resource_classes = [ArtistResource]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'view/<int:object_id>/',
                self.admin_site.admin_view(self.view_object),
                name='artist_view_object',
            ),
        ]
        return custom_urls + urls

    def view_object(self, request, object_id, *args, **kwargs):
        artist = get_object_or_404(Artist, pk=object_id)
        context = dict(
            self.admin_site.each_context(request),
            title=artist.name,
            artist=artist,
            tracks=artist.tracks.select_related('distributor'),
        )
        return render(request, 'admin/artist/artist_detail.html', context)

    @admin.display(description='UUID')
    def view_object_link(self, obj):
        url = reverse('admin:artist_view_object', args=[obj.id])
        return format_html(f'<a href="{url}">{obj.uuid}</a>')

    @admin.display(description='Husbpot')
    def artist_hubspot_link(self, obj):
        if obj.hubspot_id:
            return format_html(f'<a href="{obj.get_hubspot_url()}" target="_blank">{obj.hubspot_id}</a>')
        return ''
    
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
