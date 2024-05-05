from django.shortcuts import render
from rest_framework import viewsets, filters
from common.api.pagination import StandardPagination
from content.models import Article
from content.serializers import ArticleSerializer


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = []
    authentication_classes = []
    queryset = Article.objects.filter(published=True)
    serializer_class = ArticleSerializer
    pagination_class = StandardPagination
    lookup_field = 'uuid'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['order']