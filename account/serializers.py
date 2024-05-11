import base64
from rest_framework import serializers, fields
from rest_registration.api.serializers import DefaultUserProfileSerializer, DefaultRegisterUserSerializer
from django.contrib.auth import get_user_model
from artist.models import Artist
from account.models import Account


User = get_user_model()


class RegisterSerializer(DefaultRegisterUserSerializer):
    #profile = fields.JSONField(write_only=True, default=dict, initial=dict)
    
    class Meta:
        model = User
        
    def get_fields(self):
        fields = super().get_fields()
        fields['type'] = serializers.ChoiceField(choices=['artist', 'artist'])
        return fields

    def create(self, validated_data):
        data = validated_data.copy()
        
        user_type = data.pop('type')

        # set username as base64 email
        data['username'] = data['email']
        if self.has_password_confirm_field():
            del data['password_confirm']
        
        # create user
        user = self.Meta.model.objects.create_user(**data)
        # create related account
        Account.objects.create(user=user)

        if user_type == 'artist':
            # create related artist profile
            Artist.objects.create(user=user)
        
        #profile_data = validated_data.pop('profile')
        # update profile
        #profile = user.artist
        #for attr, value in profile_data.items():
        #    setattr(profile, attr, value)
        #profile.save()
        return user



class UserProfileSerializer(DefaultUserProfileSerializer):
    profile = fields.JSONField(write_only=True, default=dict, initial=dict)

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
