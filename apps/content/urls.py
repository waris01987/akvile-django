from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.content.views import (
    ArticleViewSet,
    CategoryViewSet,
    PeriodViewSet,
    PeriodViewSetOld,
    SubCategoryViewSet,
)


router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="articles")
router.register("categories", CategoryViewSet, basename="categories")
router.register("subcategories", SubCategoryViewSet, basename="subcategories")
router.register("periods", PeriodViewSetOld, basename="periods-old")
router.register("periods-v2", PeriodViewSet, basename="periods")

urlpatterns = [path("", include(router.urls))]
