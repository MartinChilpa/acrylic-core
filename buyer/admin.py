from django.contrib import admin
from buyer.models import Tier, Buyer


@admin.register(Tier)
class TierAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'code', 'name', 'description']


@admin.register(Buyer)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'user', 'tier', 'created', 'updated']
    list_filter = ['tier', 'created', 'updated']
    search_fields = ['user__email', 'user__username', 'tier__name', 'tier__code']
