from django.contrib import admin
import nested_admin

from apps.content.models import (
    Article,
    ArticleTranslation,
    Category,
    CategoryTranslation,
    ContentRule,
    Period,
    PeriodTranslation,
    SubCategory,
    SubCategoryTranslation,
    UserArticle,
)


class ContentRuleInline(nested_admin.NestedTabularInline):
    model = ContentRule
    extra = 0


class ArticleTranslationInline(nested_admin.NestedStackedInline):
    model = ArticleTranslation
    extra = 0


@admin.register(Article)
class ArticleAdmin(nested_admin.NestedModelAdmin):
    list_display = ["name", "category", "subcategory", "period", "is_published"]
    search_fields = ["name", "translations__title", "is_published"]
    inlines = [ArticleTranslationInline, ContentRuleInline]


class CategoryTranslationInline(nested_admin.NestedTabularInline):
    model = CategoryTranslation
    extra = 0


@admin.register(Category)
class CategoryAdmin(nested_admin.NestedModelAdmin):
    list_display = ["name"]
    search_fields = ["name", "translations__title"]
    inlines = [CategoryTranslationInline]


class SubCategoryTranslationInline(nested_admin.NestedTabularInline):
    model = SubCategoryTranslation
    extra = 0


@admin.register(SubCategory)
class SubCategoryAdmin(nested_admin.NestedModelAdmin):
    list_display = ["name", "category"]
    search_fields = ["name", "translations__title"]
    inlines = [SubCategoryTranslationInline]


class PeriodTranslationInline(nested_admin.NestedTabularInline):
    model = PeriodTranslation
    extra = 0


@admin.register(Period)
class PeriodAdmin(nested_admin.NestedModelAdmin):
    list_display = ["name"]
    search_fields = ["name", "translations__title"]
    inlines = [PeriodTranslationInline]


@admin.register(UserArticle)
class ArticleUserAdmin(admin.ModelAdmin):
    list_display = ["article", "user", "is_read"]
    search_fields = ["article__name", "user__email"]
    list_filter = ["is_read"]

    def has_change_permission(self, request, obj=None):
        return False
