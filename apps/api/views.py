from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.api import CheckAppVersionResultType
from apps.api.serializers import CheckAppVersionSerializer


class CheckAppVersionView(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = CheckAppVersionSerializer

    @extend_schema(
        description="Checks application version. Possible 'validation_result' field values: {}".format(
            ", ".join([item[0] for item in CheckAppVersionResultType.get_choices()])
        )
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class BuildVersionView(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        version = settings.BUILD_VERSION
        return Response(int(version) if version else 0)
