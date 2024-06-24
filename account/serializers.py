import base64
from rest_framework import serializers, fields
from rest_registration.api.serializers import DefaultUserProfileSerializer, DefaultRegisterUserSerializer
from django.contrib.auth import get_user_model
from artist.models import Artist
from account.models import Account, Document, Invitation


User = get_user_model()


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        exclude = ['id', 'user']


class AccountUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['billing_email', 'billing_details', 'country_code', 'phone', 'tax_id', 'failed_payment_notifications']


class RegisterDoneSerializer(DefaultRegisterUserSerializer):
    class Meta:
        model = User


class RegisterSerializer(DefaultRegisterUserSerializer):
    #profile = fields.JSONField(write_only=True, default=dict, initial=dict)
    
    class Meta:
        model = User
    
    def validate_email(self, value):
        # invite
        if not Invitation.objects.filter(email=value).exists():
            raise serializers.ValidationError('User with this email has not been invited')

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('User with this email already exists')
        return value
    
    def get_fields(self):
        fields = super().get_fields()
        fields['type'] = serializers.ChoiceField(choices=['artist', 'artist'])
        fields['spotify_url'] = serializers.URLField(required=False)
        return fields

    def create(self, validated_data):
        data = validated_data.copy()
        
        user_type = data.pop('type')
        
        spotify_url = ''
        if user_type == 'artist':
            # additional artist data
            spotify_url = data.pop('spotify_url')
        
        # set email as username
        data['username'] = base64.b64encode(data['email'].encode('utf-8')).decode('utf-8')
        if self.has_password_confirm_field():
            del data['password_confirm']
        
        # create user
        user = self.Meta.model.objects.create_user(**data)
        # create related account
        Account.objects.create(user=user)

        # mark invitation as joined
        invitations = Invitation.objects.filter(email=user.email)
        if len(invitations) > 0:
            invitation = invitations[0]
            invitation.joined = True
            invitation.save()

        if user_type == 'artist':
            # create related artist profile
            artist = Artist.objects.create(user=user, spotify_url=spotify_url)
        
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


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['uuid', 'name', 'document', 'type', 'created', 'updated']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
