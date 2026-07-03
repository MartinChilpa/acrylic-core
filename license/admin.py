from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from import_export.admin import ExportMixin
from import_export import resources, fields as ie_fields

from license.models import License
from license.tasks import build_whitelist_email


class LicenseResource(resources.ModelResource):
    transaction_date = ie_fields.Field(attribute='created', column_name='Transaction Date')
    club_name = ie_fields.Field(column_name='Club Name')
    artist_name = ie_fields.Field(column_name='Artist Name')
    track_title = ie_fields.Field(column_name='Track Title')
    isrc = ie_fields.Field(column_name='ISRC')
    tier_col = ie_fields.Field(attribute='tier', column_name='Tier')
    ecu_col = ie_fields.Field(attribute='extended_commercial_use', column_name='Extended Commercial Use')
    currency_col = ie_fields.Field(attribute='currency', column_name='Currency')
    price_col = ie_fields.Field(attribute='price', column_name='Price')
    ecu_unit_col = ie_fields.Field(attribute='ecu_unit', column_name='ECU Unit')
    revenue_col = ie_fields.Field(column_name='Revenue')

    def dehydrate_club_name(self, obj):
        return obj.club.club_name

    def dehydrate_artist_name(self, obj):
        return obj.track.artist.name if obj.track.artist else ''

    def dehydrate_track_title(self, obj):
        return obj.track.name

    def dehydrate_isrc(self, obj):
        return obj.track.isrc

    def dehydrate_revenue_col(self, obj):
        return obj.revenue

    class Meta:
        model = License
        fields = ('transaction_date', 'club_name', 'artist_name', 'track_title',
                  'isrc', 'tier_col', 'ecu_col', 'currency_col',
                  'price_col', 'ecu_unit_col', 'revenue_col')
        export_order = fields


@admin.register(License)
class LicenseAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = LicenseResource
    list_display  = ['club', 'track', 'status', 'tier', 'extended_commercial_use', 'email_sent', 'created']
    list_filter   = ['status', 'tier', 'extended_commercial_use', 'email_sent']
    search_fields = ['club__club_name', 'track__name', 'track__isrc']
    readonly_fields = ['email_error', 'email_sent', 'created', 'updated', 'uuid', 'tier', 'price', 'currency', 'ecu_unit', 'revenue']
    raw_id_fields = ['club', 'track']

    actions = ['resend_whitelist_email']

    @admin.action(description='Resend whitelist email to distributor')
    def resend_whitelist_email(self, request, queryset):
        for license_obj in queryset:
            subject, from_email, to_email, body, reply_to = build_whitelist_email(license_obj)
            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=from_email,
                    recipient_list=[to_email],
                    headers={'Reply-To': reply_to},
                )
                license_obj.email_sent = True
                license_obj.email_error = ''
                license_obj.save(update_fields=['email_sent', 'email_error', 'updated'])
            except Exception as e:
                license_obj.email_error = str(e)
                license_obj.save(update_fields=['email_error', 'updated'])
        self.message_user(request, f'Processed {queryset.count()} request(s).')
