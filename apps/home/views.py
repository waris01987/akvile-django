import logging

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.db.models import Prefetch, Subquery
from drf_spectacular.utils import extend_schema
from fcm_django.api.rest_framework import FCMDeviceViewSet
import requests
from rest_framework import status, permissions, exceptions
from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.home.models import (
    AboutAndNoticeSection,
    AboutAndNoticeSectionTranslation,
    Review,
    GlobalVariables,
)
from apps.home.serializers import (
    AboutSerializer,
    UserAboutSerializer,
    ReviewSerializer,
    GlobalVariablesSerializer,
)
from apps.users.serializers import BaseEmailSerializer

LOGGER = logging.getLogger("app")


class AboutViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AboutSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = self.request.user
        language_code = user.language.code if user.is_authenticated else settings.DEFAULT_LANGUAGE

        latest_versions_ids = Subquery(AboutAndNoticeSection.get_latest_versions().values_list("id", flat=True))
        translations = Prefetch(
            lookup="translations",
            queryset=AboutAndNoticeSectionTranslation.objects.filter(language=language_code),
            to_attr="user_translations",
        )
        queryset = AboutAndNoticeSection.objects.prefetch_related(translations).filter(id__in=latest_versions_ids)
        return queryset

    @action(detail=False, methods=["post"], serializer_class=UserAboutSerializer)
    def accept_about(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CustomFCMDeviceViewSet(FCMDeviceViewSet):
    """The custom create method allows creating and updating FCM device instances through the same one endpoint"""

    def get_object(self):
        try:
            obj = super().get_object()
        except MultipleObjectsReturned:
            # Needed to override this method due to duplicate FCMDevices. Though it is not allowing creating two
            # devices with same registration_id but still it is creating two device object with same information
            # sometimes. To handle that situation we're returning one device from multiple devices with
            # the same registration_id
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            LOGGER.error(
                "Multiple devices found with registration_id [%s].",
                self.kwargs[lookup_url_kwarg],
            )

            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
            queryset = self.filter_queryset(self.get_queryset())
            obj = queryset.filter(**filter_kwargs).first()
            self.check_object_permissions(self.request, obj)
        return obj

    def create(self, request, *args, **kwargs):
        serializer = None
        is_update = False
        if self.lookup_field in request.data:
            instance = self.queryset.filter(registration_id=request.data[self.lookup_field]).first()
            if instance:
                serializer = self.get_serializer(instance, data=request.data)
                is_update = True
        if not serializer:
            serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        if is_update:
            self.perform_update(serializer)
            return Response(serializer.data)
        else:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class SubscribeToNewsLetter(generics.CreateAPIView):
    serializer_class = BaseEmailSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {settings.MAILCHIMP_API_KEY}",
        }
        response = requests.post(
            settings.MAILCHIMP_URL,
            headers=headers,
            json={"email_address": email, "status": "subscribed"},
        )
        if response.status_code != 200:
            raise exceptions.ValidationError(
                {"non_field_errors": ["error_" + response.json()["title"].lower().replace(" ", "_")]}
            )
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class ReviewViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = (permissions.AllowAny,)
    queryset = Review.objects.order_by("-id")


class GlobalVariablesView(APIView):
    @extend_schema(responses=GlobalVariablesSerializer)
    def get(self, request):
        if request.user.is_superuser:
            return Response({"hop": "hop"})
        instance = GlobalVariables.objects.first()
        return Response(GlobalVariablesSerializer(instance=instance).data)


class ClearScrappedProductsView(APIView):
    def get(self, request):
        from django.core.management import call_command

        if not request.user.is_superuser:
            return Response({"error": "you are not superuser"})
        call_command("delete_empty_products")
        return Response({"message": "done"})
