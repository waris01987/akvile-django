from django.urls import path

from apps.csv_read.views import RemoveUpdate

urlpatterns = [
    path(
        "remove-failed-data",
        RemoveUpdate.as_view(),
        name="remove-failed-data",
    ),
]
