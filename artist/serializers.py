from rest_framework import serializers, fields
from django.contrib.auth import get_user_model

from artist.models import Artist


User = get_user_model()


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        #fields = '__all__'
        exclude = ['id', 'user']


class ArtistUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ['name', 'bio', 'slug', 'hometown', 'country', 'image', 'background_image']