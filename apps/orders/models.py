from django.db import models

from apps.orders import Currency
from apps.users.models import User
from apps.utils.models import UUIDBaseModel


class Order(UUIDBaseModel):
    user = models.ForeignKey(User, related_name="orders", on_delete=models.PROTECT)
    shopify_order_id = models.CharField(max_length=255)
    shopify_order_date = models.DateTimeField()
    total_price = models.PositiveBigIntegerField()  # type: ignore
    currency = models.CharField(
        max_length=3,
        choices=Currency.get_choices(),
        default=Currency.EUR.value,
        editable=False,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.shopify_order_id}"
