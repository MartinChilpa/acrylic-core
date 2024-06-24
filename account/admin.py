from django.contrib import admin
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from account.models import Account, Document, Invitation


class ImportExportResource(resources.ModelResource):
    def get_import_fields(self):
        fields = super().get_import_fields()
        return [f for f in fields if f.attribute in self._meta.import_fields]

    def get_export_fields(self):
        fields = super().get_export_fields()
        return [f for f in fields if f.attribute in self._meta.export_fields]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'user', 'billing_email', 'phone', 'tax_id', 'created', 'updated']
    search_fields = ['uuid', 'user__email', 'tax_id', 'billing_email', 'phone']
    raw_id_fields = ['user']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'name', 'user', 'document', 'type', 'signed', 'created', 'updated']
    list_filter = ['type', 'signed', 'created', 'updated']
    search_fields = ['uuid', 'name']
    raw_id_fields = ['user']


class InvitationResource(ImportExportResource):
    class Meta:
        model = Invitation
        fields = ['id', 'email']
        #exclude = ['id']
        import_fields = ['email']
        export_fields = ['uuid', 'email', 'joined', 'created', 'updated']


@admin.register(Invitation)
class InvitationAdmin(ImportExportModelAdmin):
    list_display = ['email', 'invited_by', 'language', 'joined', 'created', 'updated']
    search_fields = ['email']
    raw_id_fields = ['invited_by']
    resource_classes = [InvitationResource]
