"""
urls.py
API level urls
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from watchman.views import bare_status

from apps.api.views import CheckAppVersionView, BuildVersionView

router = DefaultRouter()

urlpatterns = [
    path("orders/", include("apps.orders.urls")),
    path("routines/", include("apps.routines.urls")),
    path("content/", include("apps.content.urls")),
    path("questionnaire/", include("apps.questionnaire.urls")),
    path("health/", bare_status, name="watchman"),
    path("build-version/", BuildVersionView.as_view(), name="build-version"),
    path("home/", include("apps.home.urls")),
    path("users/", include("apps.users.urls")),
    path("check-app-version/", CheckAppVersionView.as_view(), name="check-app-version"),
    path("manifests/", include("apps.manifests.urls")),
    path("monetization/", include("apps.monetization.urls")),
    path("chat_gpt/", include("apps.chat_gpt.urls")),
    path("update-geo/", include("apps.csv_read.urls")),
]
