import django_filters

from apps.content.models import Article


class ArticleFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="category_id")
    subcategory = django_filters.NumberFilter(field_name="subcategory_id")

    class Meta:
        model = Article
        fields = ["category", "subcategory"]
