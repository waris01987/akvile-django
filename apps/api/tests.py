from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from apps.api import CheckAppVersionResultType
from apps.home.models import SiteConfiguration
from apps.utils.tests_utils import BaseTestCase


class WatchmanCase(BaseTestCase):
    def test_watchman_state(self):
        response = self.client.get(reverse("watchman"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BuildVersionCase(BaseTestCase):
    @override_settings(BUILD_VERSION=123)
    def test_build_version(self):
        response = self.client.get(reverse("build-version"))
        self.assertEqual(response.json(), 123)


class CheckAppVersionCase(BaseTestCase):
    """
    Sligtly violating principle of tests being atomic in order to cover more cases without too many lines of code
    """

    def test_if_nothing_configured_every_version_is_ok(self):
        self._test_check_app_version("0", CheckAppVersionResultType.OK)
        self._test_check_app_version("v0", CheckAppVersionResultType.OK)
        self._test_check_app_version("0.1", CheckAppVersionResultType.OK)
        self._test_check_app_version("v0.1", CheckAppVersionResultType.OK)
        self._test_check_app_version("1.2.3", CheckAppVersionResultType.OK)
        self._test_check_app_version("v1.2.3", CheckAppVersionResultType.OK)
        self._test_check_app_version("4.5.6", CheckAppVersionResultType.OK)
        self._test_check_app_version("v4.5.6", CheckAppVersionResultType.OK)
        self._test_check_app_version("123", CheckAppVersionResultType.OK)
        self._test_check_app_version("v123", CheckAppVersionResultType.OK)
        self._test_check_app_version("abc", CheckAppVersionResultType.OK)

    def test_if_configured_without_v_prefix(self):
        self._set_configuration(minimal_version="1.2.3", latest_version="4.5.6")
        self._test_check_app_version("0", CheckAppVersionResultType.NOT_OK_UPDATE_REQUIRED)
        self._test_check_app_version("v0", CheckAppVersionResultType.NOT_OK_UPDATE_REQUIRED)
        self._test_check_app_version("0.1", CheckAppVersionResultType.NOT_OK_UPDATE_REQUIRED)
        self._test_check_app_version("v0.1", CheckAppVersionResultType.NOT_OK_UPDATE_REQUIRED)
        self._test_check_app_version("1.2.3", CheckAppVersionResultType.OK_UPDATE_RECOMMENDED)
        self._test_check_app_version("v1.2.3", CheckAppVersionResultType.OK_UPDATE_RECOMMENDED)
        self._test_check_app_version("4.5.6", CheckAppVersionResultType.OK)
        self._test_check_app_version("v4.5.6", CheckAppVersionResultType.OK)
        self._test_check_app_version("123", CheckAppVersionResultType.OK)
        self._test_check_app_version("v123", CheckAppVersionResultType.OK)
        self._test_check_app_version("abc", CheckAppVersionResultType.NOT_OK_UPDATE_REQUIRED)

    def test_if_configured_with_v_prefix(self):
        self._set_configuration(minimal_version="v1.2.3", latest_version="v4.5.6")
        self._test_check_app_version("0", CheckAppVersionResultType.NOT_OK_UPDATE_REQUIRED)
        self._test_check_app_version("v0", CheckAppVersionResultType.NOT_OK_UPDATE_REQUIRED)
        self._test_check_app_version("0.1", CheckAppVersionResultType.NOT_OK_UPDATE_REQUIRED)
        self._test_check_app_version("v0.1", CheckAppVersionResultType.NOT_OK_UPDATE_REQUIRED)
        self._test_check_app_version("1.2.3", CheckAppVersionResultType.OK_UPDATE_RECOMMENDED)
        self._test_check_app_version("v1.2.3", CheckAppVersionResultType.OK_UPDATE_RECOMMENDED)
        self._test_check_app_version("4.5.6", CheckAppVersionResultType.OK)
        self._test_check_app_version("v4.5.6", CheckAppVersionResultType.OK)
        self._test_check_app_version("123", CheckAppVersionResultType.OK)
        self._test_check_app_version("v123", CheckAppVersionResultType.OK)
        self._test_check_app_version("abc", CheckAppVersionResultType.NOT_OK_UPDATE_REQUIRED)

    def _set_configuration(self, minimal_version: str, latest_version: str) -> None:
        site_config = SiteConfiguration.get_solo()
        site_config.app_version_minimal_supported = minimal_version
        site_config.app_version_latest = latest_version
        site_config.save(update_fields=["app_version_minimal_supported", "app_version_latest"])

    def _test_check_app_version(self, passed_version: str, expected_result: CheckAppVersionResultType) -> None:
        response = self.client.post(reverse("check-app-version"), data={"app_version": passed_version})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["validation_result"], expected_result.value)  # type: ignore
