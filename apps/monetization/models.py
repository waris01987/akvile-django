from django.db import models

from apps.utils.models import BaseModel


class StoreProduct(BaseModel):
    name = models.CharField(unique=True, max_length=55)
    description = models.CharField(max_length=200)
    sku = models.CharField(
        unique=True,
        max_length=154,
        help_text="Stock Keeping Unit - alphanumeric identifier from stores",
    )
    is_enabled = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name
