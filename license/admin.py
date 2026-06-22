from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings

from license.models import License
from license.tasks import build_whitelist_email


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display  = ['club', 'track', 'status', 'email_sent', 'created']
    list_filter   = ['status', 'email_sent']
    search_fields = ['club__club_name', 'track__name', 'track__isrc']
    readonly_fields = ['email_error', 'email_sent', 'created', 'updated', 'uuid']
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
