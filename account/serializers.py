import base64
from rest_framework import serializers, fields
from rest_registration.api.serializers import DefaultUserProfileSerializer, DefaultRegisterUserSerializer
from django.contrib.auth import get_user_model
from artist.models import Artist
from club.models import Club
from label.models import Label
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
    
    # def validate_email(self, value):
    #     # invite
        
    #     if not Invitation.objects.filter(email=value).exists():
    #         raise serializers.ValidationError('User with this email has not been invited')

    #     if User.objects.filter(email=value).exists():
    #         print("Existe?")
    #         raise serializers.ValidationError('User with this email already exists')
    #     return value

    def validate(self, attrs):
        """
        Validación integral: aquí tenemos acceso a 'email' y a 'type'.
        """
        email = attrs.get('email')
        user_type = attrs.get('type')

        # 1. Validar si el usuario ya existe (aplica para todos)
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': 'User with this email already exists'})

        # 2. VALIDACIÓN CONDICIONAL: 
        # Solo pedimos invitación si el tipo es 'artist'. 
        # Los 'club' pasan directo sin invitación.
        if user_type == 'artist':
            if not Invitation.objects.filter(email=email).exists():
                raise serializers.ValidationError({
                    'email': 'Artists must have an invitation to register.'
                })
        return attrs

    
    def get_fields(self):
        fields = super().get_fields()
        fields['type'] = serializers.ChoiceField(choices=['artist', 'club', 'label'])
        fields['spotify_url'] = serializers.URLField(required=False)
        fields['label_name'] = serializers.CharField(required=False)
        return fields

    def create(self, validated_data):
        data = validated_data.copy()
        
        user_type = data.pop('type')
        spotify_url = data.pop('spotify_url',' ')
        label_name = data.pop('label_name', None)
                    
        
        # set email as username
        data['username'] = base64.b64encode(data['email'].encode('utf-8')).decode('utf-8')
        if self.has_password_confirm_field():
            del data['password_confirm']
        
        # create user
        user = self.Meta.model.objects.create_user(**data)

        if user_type=='artist':
            db_user_type = Account.UserType.ARTIST
        elif user_type=='club':
            db_user_type = Account.UserType.CLUB
        elif user_type=='label':
            db_user_type = Account.UserType.LABEL
        else:
            db_user_type = Account.UserType.UND


        # create related account
        Account.objects.create(user=user,user_type=db_user_type)

        # mark invitation as joined
        invitations = Invitation.objects.filter(email=user.email)
        if len(invitations) > 0:
            invitation = invitations[0]
            invitation.joined = True
            invitation.save()


        if 'club' == user_type:
            club = Club.objects.create(user=user,club_name=user.first_name)
            print("REGISTRO DE CLUB DETECTADO:")
            

        if user_type == 'artist':
            # create related artist profile
            artist = Artist.objects.create(user=user, spotify_url=spotify_url)

        if user_type == 'label':
            Label.objects.create(
                user=user,
                label_name=(user.first_name),
            )
        
        
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
