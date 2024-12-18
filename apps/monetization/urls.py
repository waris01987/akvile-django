from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.monetization.views import StoreProductViewSet

store_products_router = DefaultRouter()
store_products_router.register("products", StoreProductViewSet, basename="products")

urlpatterns = [
    path("", include(store_products_router.urls)),
]
