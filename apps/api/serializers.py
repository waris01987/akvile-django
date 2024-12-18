from packaging import version
from rest_framework import serializers

from apps.api import CheckAppVersionResultType
from apps.home.models import SiteConfiguration


class CheckAppVersionSerializer(serializers.Serializer):
    app_version = serializers.CharField(required=True, write_only=True)
    validation_result = serializers.CharField(read_only=True)
    latest_version = serializers.CharField(read_only=True)

    def create(self, validated_data):
        site_config = SiteConfiguration.get_solo()
        return {
            "validation_result": self._get_validation_status(
                given_version=validated_data["app_version"],
                minimal_version=site_config.app_version_minimal_supported,
                latest_version=site_config.app_version_latest,
            ).value,
            "latest_version": site_config.app_version_latest,
        }

    def _get_validation_status(
        self,
        given_version: str,
        minimal_version: str,
        latest_version: str,
    ) -> CheckAppVersionResultType:
        if self._version_smaller_than(given_version, minimal_version):
            return CheckAppVersionResultType.NOT_OK_UPDATE_REQUIRED
        elif self._version_smaller_than(given_version, latest_version):
            return CheckAppVersionResultType.OK_UPDATE_RECOMMENDED
        else:
            return CheckAppVersionResultType.OK

    def _version_smaller_than(self, version1: str, version2: str) -> bool:
        return version.parse(version1) < version.parse(version2) if version1 and version2 else False
