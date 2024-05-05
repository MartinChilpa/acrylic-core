from rest_framework import serializers
from legal.models import SplitSheet, MasterSplit, PublishingSplit


class MasterSplitSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterSplit
        fields = ['uuid', 'role',  'name', 'legal_name', 'email', 'percent', 'signed']


class PublishingSplitSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterSplit
        fields = ['uuid', 'role', 'name', 'legal_name', 'email', 'percent', 'signed', 'pro_name', 'ipi']



class SplitSheetSerializer(serializers.ModelSerializer):
    publishing_splits = PublishingSplitSerializer(many=True, required=True)
    master_splits = MasterSplitSerializer(many=True, required=True)

    class Meta:
        model = SplitSheet
        fields = ['track', 'track_name', 'signed', 'signature_request_id', 'created', 'updated']

    def create(self, validated_data):
        publishing_splits_data = validated_data.pop('publishing_splits', [])
        master_splits_data = validated_data.pop('master_splits', [])

        split_sheet = SplitSheet.objects.create(**validated_data)

        for publishing_split_data in publishing_splits_data:
            PublishingSplit.objects.create(split_sheet=split_sheet, **publishing_split_data)

        for master_split_data in master_splits_data:
            MasterSplit.objects.create(split_sheet=split_sheet, **master_split_data)

        return split_sheet

    def update(self, instance, validated_data):
        publishing_splits_data = validated_data.pop('publishing_splits', [])
        master_splits_data = validated_data.pop('master_splits', [])

        instance.track_name = validated_data.get('track_name', instance.track_name)
        instance.save()
        
        # Update or create publishing splits
        for publishing_split_data in publishing_splits_data:
            publishing_split_uuid = publishing_split_data.get('uuid', None)
            if publishing_split_uuid:
                publishing_split = PublishingSplit.objects.get(split_sheet=instance, uuid=publishing_split_uuid)
                publishing_split.name = publishing_split_data.get('name', publishing_split.name)
                # Update other fields as necessary
                publishing_split.save()
            else:
                PublishingSplit.objects.create(split_sheet=instance, **publishing_split_data)

        # Update or create master splits
        for master_split_data in master_splits_data:
            master_split_uuid = master_split_data.get('uuid', None)
            if master_split_uuid:
                master_split = MasterSplit.objects.get(uuid=master_split_uuid)
                master_split.name = master_split_data.get('name', master_split.name)
                # Update other fields as necessary
                master_split.save()
            else:
                MasterSplit.objects.create(split_sheet=instance, **master_split_data)

        return instance
