from rest_framework import serializers
from content.models import Article


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['title', 'image', 'link_text', 'url', 'order']
