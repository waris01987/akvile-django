from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.home.views import (
    AboutViewSet,
    CustomFCMDeviceViewSet,
    SubscribeToNewsLetter,
    ReviewViewSet,
    GlobalVariablesView,
    ClearScrappedProductsView,
)

router = DefaultRouter()

router.register("about", AboutViewSet, basename="about")
router.register("devices", CustomFCMDeviceViewSet, basename="devices")
router.register("reviews", ReviewViewSet, basename="reviews")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "newsletter/subscribe/",
        SubscribeToNewsLetter.as_view(),
        name="newsletter-subscribe",
    ),
    path("global-variables/", GlobalVariablesView.as_view(), name="global_variables"),
    path(
        "clear-scrapped-products/",
        ClearScrappedProductsView.as_view(),
        name="clear_scrapped_products",
    ),
]
