import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models


class UUIDBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)  # noqa A003

    class Meta:
        abstract = True


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseTranslationModel(models.Model):
    """
    Base class for translations models.
    """

    language = models.ForeignKey(
        "translations.Language",
        default=settings.DEFAULT_LANGUAGE,
        on_delete=models.CASCADE,
    )
    title = models.TextField()

    class Meta:
        abstract = True
        indexes = [GinIndex(fields=["title"])]

    def __str__(self):
        return self.title
