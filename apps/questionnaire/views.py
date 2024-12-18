import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.questionnaire.models import UserQuestionnaire
from apps.questionnaire.serializers import MakeUpSerializer, UserQuestionnaireSerializer
from apps.utils.error_codes import Errors

LOGGER = logging.getLogger("app")


class UserQuestionnaireViewSet(viewsets.ModelViewSet):
    serializer_class = UserQuestionnaireSerializer

    def get_queryset(self):
        return UserQuestionnaire.objects.filter(user=self.request.user)

    def partial_update(self, request, pk=None):
        return Response(
            Errors.PARTIAL_UPDATE_DISABLED.value,
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(
        detail=True,
        methods=["post", "put"],
        url_path="add-make-up",
        url_name="add-make-up",
    )
    def add_make_up(self, request, pk=None):
        questionnaire = self.get_object()
        serializer = MakeUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        questionnaire.make_up = serializer.validated_data["make_up"]
        questionnaire.save(update_fields=["make_up"])
        return Response(data=serializer.data)
