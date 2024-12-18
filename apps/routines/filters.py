from django.contrib.admin import SimpleListFilter
from django.db.models import Q
import django_filters

from apps.routines.models import (
    Routine,
    DailyProductGroup,
    DailyProduct,
    ScrapedProduct,
)


class RoutineFilter(django_filters.FilterSet):
    created_at = django_filters.DateFilter(field_name="created_at__date", input_formats=["%Y-%m-%d"])

    class Meta:
        model = Routine
        fields = ["created_at"]


class ScrapedProductFilter(django_filters.FilterSet):
    want = django_filters.BooleanFilter(field_name="products__want", method="filter_want")
    have = django_filters.BooleanFilter(field_name="products__have", method="filter_have")

    def filter_want(self, queryset, name, value):
        if value is False:
            return queryset.filter(Q(products__isnull=True) | Q(products__want=False))
        else:
            return queryset.filter(products__want=True)

    def filter_have(self, queryset, name, value):
        if value is False:
            return queryset.filter(Q(products__isnull=True) | Q(products__have=False))
        else:
            return queryset.filter(products__have=True)

    class Meta:
        model = ScrapedProduct
        fields = ["recommended_product", "type", "want", "have"]


class IsCompletedFilter(SimpleListFilter):
    title = "Completed"
    parameter_name = "completed"

    def lookups(self, request, model_admin):
        return (("True", True), ("False", False))

    def queryset(self, request, queryset):
        filters = {
            DailyProductGroup: Q(products__name__exact="")
            | Q(products__brand__exact="")
            | Q(products__ingredients__exact="")
            | Q(products__size__exact=""),
            DailyProduct: Q(name__exact="") | Q(brand__exact="") | Q(ingredients__exact="") | Q(size__exact=""),
        }

        data = {"True": queryset.exclude, "False": queryset.filter}
        function = data.get(self.value())

        if function and queryset.model in filters:
            return function(filters[queryset.model]).distinct()
        return queryset
