from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.monetization.models import StoreProduct
from apps.monetization.serializers import StoreProductSerializer


class StoreProductViewSet(ReadOnlyModelViewSet):
    queryset = StoreProduct.objects.filter(is_enabled=True)
    serializer_class = StoreProductSerializer
