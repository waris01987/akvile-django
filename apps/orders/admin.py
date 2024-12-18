from django.contrib import admin
from import_export.admin import ExportMixin
from import_export.formats import base_formats

from apps.orders.models import Order
from apps.orders.resources import OrderResource


@admin.register(Order)
class OrderAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = OrderResource
    fields = [
        "user",
        "shopify_order_id",
        "shopify_order_date",
        "currency",
        "total_price_in_eur",
    ]
    list_display = [
        "user",
        "shopify_order_id",
        "shopify_order_date",
        "currency",
        "total_price_in_eur",
    ]
    search_fields = ["user__email", "shopify_order_id", "currency"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_export_formats(self):
        formats = (
            base_formats.CSV,
            base_formats.XLSX,
        )
        return [f for f in formats if f().can_export()]

    def get_export_queryset(self, request):
        qs = Order.objects.select_related("user")
        return qs

    def total_price_in_eur(self, obj):
        return obj.total_price / 100
