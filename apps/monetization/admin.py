from django.contrib import admin

from apps.monetization.models import StoreProduct


@admin.register(StoreProduct)
class StoreProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "sku",
        "is_default",
        "is_enabled",
        "created_at",
        "updated_at",
    ]
