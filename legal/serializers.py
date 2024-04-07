from rest_framework import serializers
from legal.models import MasterSplit, PublishingSplit


class MasterSplitSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterSplit
        fields = ['uuid', 'owner_name', 'owner_email', 'percent', 'validated']
