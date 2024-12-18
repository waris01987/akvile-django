from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.manifests.views import AppConfigView

router = DefaultRouter()

urlpatterns = [
    path("app-config/", AppConfigView.as_view(), name="app-config"),
]
