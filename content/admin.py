from django.contrib import admin
from content.models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'link_text', 'url', 'order', 'published', 'created', 'updated']
    list_filter = ['published', 'created', 'updated']
