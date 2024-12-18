from rest_framework import serializers

from apps.monetization.models import StoreProduct


class StoreProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreProduct
        fields = ["id", "name", "description", "sku", "is_enabled", "is_default"]
