from rest_framework import serializers, fields
from rest_registration.api.serializers import DefaultUserProfileSerializer, DefaultRegisterUserSerializer
from django.contrib.auth import get_user_model

from artist.models import Artist


User = get_user_model()


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        #fields = '__all__'
        exclude = ['id']


class RegisterArtistSerializer(DefaultRegisterUserSerializer):
    #profile = fields.JSONField(write_only=True, default=dict, initial=dict)

    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm']

    #def get_fields(self, *args, **kwargs):
    #    obj_fields = super().get_fields()
    #    obj_fields['profile'] = fields.JSONField(write_only=True, default=dict, initial=dict)
    #    return obj_fields

    def create(self, validated_data):
        data = validated_data.copy()
        # set username as base64 email
        data['username'] = data['email']
        if self.has_password_confirm_field():
            del data['password_confirm']
        return self.Meta.model.objects.create_user(**data)
    """
    def create(self, validated_data):
        #profile_data = validated_data.pop('profile')
        user = super().create(validated_data)
        # create related artist profile
        Artist.objects.create(user=user)
        # update profile
        profile = user.artist
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()
        return user
    """