from django.contrib import admin
from django.utils.html import format_html
from account.models import Account, Document, Invitation


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'user', 'billing_email', 'phone', 'tax_id', 'created', 'updated']
    search_fields = ['uuid', 'user__email', 'tax_id', 'billing_email', 'phone']
    raw_id_fields = ['user']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'name', 'user', 'document', 'type', 'created', 'updated']
    list_filter = ['type']
    search_fields = ['uuid', 'name']
    raw_id_fields = ['user']


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'joined', 'created', 'updated']
    search_fields = ['email']

