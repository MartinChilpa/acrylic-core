from rest_framework import serializers, fields
from rest_registration.api.serializers import DefaultUserProfileSerializer, DefaultRegisterUserSerializer
from django.contrib.auth import get_user_model

from artist.models import Artist
from artist.serializers import ArtistSerializer


User = get_user_model()


class UserProfileSerializer(DefaultUserProfileSerializer):
    class Meta:
        model = User

    def get_profile_serializer(self):
        profile = user.get_profile()
        if not profile:
            return None
        profile_model = profile._meta.model.__name__
        profile_mapping = {
            'Artist': ArtistSerializer,
            'Buyer': None,
        }
        return profile_mapping[profile_model]

    def get_fields(self, *args, **kwargs):
        obj_fields = super().get_fields()
        obj_fields['profile'] = fields.JSONField(write_only=True, default=dict, initial=dict)
        return obj_fields

    def to_representation(self, instance):
        representation = super(UserProfileSerializer, self).to_representation(instance)
        ProfileSerializer = self.get_profile_serializer()
        representation['profile'] = ProfileSerializer(instance.profile, read_only=True).data
        return representation

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile')
        user = super().update(instance, validated_data)
        # update profile
        profile = user.profile
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()
        return user



class RegisterArtistSerializer(DefaultRegisterUserSerializer):
    class Meta:
        model = User

    def get_fields(self, *args, **kwargs):
        obj_fields = super().get_fields()
        obj_fields['profile'] = fields.JSONField(write_only=True, default=dict, initial=dict)
        return obj_fields

    def create(self, validated_data):
        profile_data = validated_data.pop('profile')
        user = super().create(validated_data)
        # create related artist profile
        Arist.objects.create(user=user)
        # update profile
        profile = user.artist
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()
        return user
