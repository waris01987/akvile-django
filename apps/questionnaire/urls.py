from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.questionnaire.views import UserQuestionnaireViewSet


router = DefaultRouter()
router.register("questionnaires", UserQuestionnaireViewSet, basename="questionnaire")

urlpatterns = [path("", include(router.urls))]
