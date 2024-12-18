import datetime

from django.conf import settings
from django.db.models import Prefetch, QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.content import CategoryName
from apps.content.filters import ArticleFilter
from apps.content.models import (
    Article,
    ArticleTranslation,
    Category,
    CategoryTranslation,
    Period,
    PeriodTranslation,
    SubCategory,
    SubCategoryTranslation,
    UserArticle,
)
from apps.content.serializers import (
    ArticleSerializer,
    CategorySerializer,
    PeriodSerializer,
    PeriodSerializerOld,
    SubCategorySerializer,
    SubCategoryDetailSerializer,
    CategoryDetailSerializer
)
from apps.users.models import User


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CategoryDetailSerializer
        return CategorySerializer

    def get_queryset(self):
        user = self.request.user
        language_code = user.language.code if user.is_authenticated else settings.DEFAULT_LANGUAGE
        category_translations = Prefetch(
            lookup="translations",
            queryset=CategoryTranslation.objects.filter(language=language_code),
            to_attr="user_translations",
        )
        subcategory_translations = Prefetch(
            lookup="translations",
            queryset=SubCategoryTranslation.objects.filter(language=language_code),
            to_attr="user_translations",
        )
        subcategories = Prefetch(
            "subcategories",
            queryset=SubCategory.objects.prefetch_related(subcategory_translations)
        )
        queryset = Category.objects.prefetch_related(
            category_translations,
            subcategories,
        )
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class SubCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SubCategoryDetailSerializer
        return SubCategorySerializer

    def get_queryset(self):
        user = self.request.user
        language_code = user.language.code if user.is_authenticated else settings.DEFAULT_LANGUAGE

        subcategory_translations = Prefetch(
            lookup="translations",
            queryset=SubCategoryTranslation.objects.filter(language=language_code),
            to_attr="user_translations",
        )

        nested_subcategories = Prefetch(
            "subCategories",
            queryset=SubCategory.objects.prefetch_related(subcategory_translations)
        )

        article_qs = Article.objects.filter(is_published=True)

        if user.is_authenticated:
            user_articles = Prefetch(
                "article_users",
                queryset=UserArticle.objects.filter(user=user),
                to_attr="user_article",
            )
            article_qs = article_qs.prefetch_related(user_articles)

        article_translations = Prefetch(
            "translations",
            queryset=ArticleTranslation.objects.filter(language=language_code),
            to_attr="user_translations",
        )

        article_qs = article_qs.prefetch_related(article_translations)

        articles = Prefetch(
            "articles",
            queryset=article_qs
        )

        queryset = SubCategory.objects.prefetch_related(
            subcategory_translations,
            nested_subcategories,
            articles,
        )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ArticleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ArticleFilter

    @staticmethod
    def get_article_queryset(user: User, **filters) -> QuerySet:
        language_code = user.language.code if user.is_authenticated else settings.DEFAULT_LANGUAGE

        translations = Prefetch(
            lookup="translations",
            queryset=ArticleTranslation.objects.filter(language=language_code),
            to_attr="user_translations",
        )
        user_articles = Prefetch(
            lookup="article_users",
            queryset=UserArticle.objects.filter(user=user),
            to_attr="user_article",
        )
        return Article.objects.filter(**filters).prefetch_related(user_articles, translations)

    def get_queryset(self):
        return self.get_article_queryset(self.request.user, is_published=True)

    @action(detail=True, methods=["post"], url_path="mark-as-read", url_name="mark-as-read")
    def mark_as_read(self, request, pk=None):
        article = self.get_object()
        user_article, _created = UserArticle.objects.get_or_create(article=article, user=request.user)
        user_article.is_read = True
        user_article.read_at = datetime.datetime.now(datetime.timezone.utc)
        user_article.save(update_fields=["is_read", "read_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_name="progress")
    def progress(self, request):
        all_published_user_articles = UserArticle.objects.filter(
            user=request.user,
            article__category__name__in=[
                CategoryName.CORE_PROGRAM.value,
                CategoryName.INITIAL.value,
            ],
            article__is_published=True,
        ).count()
        read_user_articles = UserArticle.objects.filter(
            user=request.user,
            article__category__name__in=[
                CategoryName.CORE_PROGRAM.value,
                CategoryName.INITIAL.value,
            ],
            is_read=True,
        ).count()
        data = {"percent_of_read_articles": 0}
        if read_user_articles:
            read_article_percentage = round(read_user_articles / all_published_user_articles * 100)
            data = {"percent_of_read_articles": read_article_percentage}
        return Response(data)

    @action(detail=False, methods=["get"], url_path="lifestyle-articles")
    def lifestyle_articles(self, request):
        lifestyle_articles = self.get_queryset().exclude(lifestyle_category="")
        serializer = self.serializer_class(lifestyle_articles, many=True)
        return Response(serializer.data)


class PeriodViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PeriodSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["intro_user_article"] = UserArticle.objects.filter(
            user=self.request.user, article__category__name=CategoryName.INITIAL.value
        ).first()
        return context

    def get_queryset(self):
        user = self.request.user
        language_code = user.language.code if user.is_authenticated else settings.DEFAULT_LANGUAGE

        translations = Prefetch(
            lookup="translations",
            queryset=PeriodTranslation.objects.filter(language=language_code),
            to_attr="user_translations",
        )
        articles = Prefetch(
            lookup="articles",
            queryset=ArticleViewSet.get_article_queryset(user, is_published=True),
            to_attr="user_articles",
        )

        queryset = Period.objects.prefetch_related(translations, articles)
        return queryset


class PeriodViewSetOld(PeriodViewSet):
    """We need to support olf flow, because apps before v2.3.0 expected different is_locked flow,
    that there is at least one non locked item. This needs to be removed after v2.3.0 is released"""

    serializer_class = PeriodSerializerOld
