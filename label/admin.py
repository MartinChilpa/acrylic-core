from django.contrib import admin

from label.models import Label


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ("label_name", "user", "is_active", "created", "updated")
    search_fields = ("label_name", "user__email")
    list_filter = ("is_active",)

