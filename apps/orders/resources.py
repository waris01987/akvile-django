from import_export import resources, fields

from apps.orders.models import Order


class OrderResource(resources.ModelResource):
    user = fields.Field("user__email", readonly=True)

    class Meta:
        model = Order
        fields = ["shopify_order_id", "shopify_order_date", "total_price", "currency"]
        export_order = ["user"]
