from rest_framework import serializers

from apps.orders.models import Order


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Order
        fields = [
            "id",
            "created_at",
            "user",
            "shopify_order_id",
            "shopify_order_date",
            "total_price",
            "currency",
        ]
