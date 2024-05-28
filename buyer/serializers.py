from rest_framework import serializers
from buyer.models import Tier


class TierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tier
        fields = ['uuid', 'code', 'name', 'description']
