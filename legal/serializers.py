from rest_framework import serializers
from legal.models import SplitSheet, MasterSplit, PublishingSplit


class MasterSplitSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterSplit
        fields = ['uuid', 'role',  'name', 'legal_name', 'email', 'percent', 'signed']


class PublishingSplitSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishingSplit
        fields = ['uuid', 'role', 'name', 'legal_name', 'email', 'percent', 'signed', 'pro_name', 'ipi']



class SplitSheetSerializer(serializers.ModelSerializer):
    track = serializers.SlugRelatedField(slug_field='uuid')
    publishing_splits = PublishingSplitSerializer(many=True, required=False)
    master_splits = MasterSplitSerializer(many=True, required=False)

    class Meta:
        model = SplitSheet
        fields = ['track', 'track_name', 'signed', 'signature_request_id', 'created', 'updated', 'publishing_splits', 'master_splits']

    def validate_track(self, value):
        user = self.context['request'].user
        artist = user.artist
        if value.artist != artist:
            raise serializers.ValidationError("The track does not belong to the requesting user's artist.")
        return value

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
                publishing_split, _ = PublishingSplit.objects.update_or_create(
                    split_sheet=instance, uuid=publishing_split_uuid,
                    defaults=publishing_split_data
                )
            else:
                PublishingSplit.objects.create(split_sheet=instance, **publishing_split_data)

        # Update or create master splits
        for master_split_data in master_splits_data:
            master_split_uuid = master_split_data.get('uuid', None)
            if master_split_uuid:
                master_split, _ = MasterSplit.objects.update_or_create(
                    split_sheet=instance, uuid=master_split_uuid,
                    defaults=master_split_data
                )
            else:
                MasterSplit.objects.create(split_sheet=instance, **master_split_data)

        return instance
