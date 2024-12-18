import json
import logging
from typing import Optional, Union
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.urls import reverse
from fcm_django.models import FCMDevice
from model_bakery.baker import make
from requests.models import Response
from rest_framework import status
from rest_framework.response import Response as DRFResponse

from apps.content import AboutAndNoticeSectionType
from apps.home.models import (
    AboutAndNoticeSection,
    AboutAndNoticeSectionTranslation,
    DashboardOrder,
    Review,
    GlobalVariables,
)
from apps.utils.error_codes import Errors
from apps.utils.tests_utils import BaseTestCase


class AboutTests(BaseTestCase):
    timestamp_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    accept_about_url = reverse("about-accept-about")
    error_messages = {
        AboutAndNoticeSectionType.TERMS_OF_SERVICE.value: Errors.INCORRECT_TERMS_OF_SERVICE_VERSION.value,
        AboutAndNoticeSectionType.PRIVACY_POLICY.value: Errors.INCORRECT_PRIVACY_POLICY_VERSION.value,
    }

    def setUp(self):
        super().setUp()
        self.about_section_1 = make(AboutAndNoticeSection, type=AboutAndNoticeSectionType.PRIVACY_POLICY.value)
        self.about_translation_1 = make(AboutAndNoticeSectionTranslation, section=self.about_section_1)

        self.about_section_2 = make(AboutAndNoticeSection, type=AboutAndNoticeSectionType.TERMS_OF_SERVICE.value)
        self.about_translation_2 = make(AboutAndNoticeSectionTranslation, section=self.about_section_2)

    def _assert_list(self, response: DRFResponse, expected_about_sections: list, status_code: int):
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(len(response.data["results"]), 2)

        for about_section, expected_about_section in zip(response.data["results"], expected_about_sections):
            self._assert_detail(about_section, *expected_about_section)

    def _assert_detail(
        self,
        data: dict,
        about_section: AboutAndNoticeSection,
        about_translation: AboutAndNoticeSectionTranslation,
        status_code: Optional[int] = None,
    ):
        if status_code:
            self.assertEqual(status_code, status.HTTP_200_OK)

        self.assertEqual(data["id"], about_section.id)
        self.assertEqual(data["title"], about_translation.title)
        self.assertEqual(data["content"], about_translation.content)
        self.assertEqual(data["type"], about_section.type)
        self.assertEqual(data["version"], about_section.version)
        self.assertEqual(data["created_at"], about_section.created_at.strftime(self.timestamp_format))
        self.assertEqual(data["updated_at"], about_section.updated_at.strftime(self.timestamp_format))

    def _assert_accept_success(self, response: DRFResponse, expected_data_ids: list):
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        expected_data = self.user.user_accepted_about_and_notice_section.filter(id__in=expected_data_ids)

        for about_and_notice_section, expected in zip(response.data, expected_data):
            self.assertEqual(about_and_notice_section["id"], expected.id)
            self.assertEqual(about_and_notice_section["user"], expected.user.id)
            self.assertEqual(
                about_and_notice_section["about_and_notice_section"],
                expected.about_and_notice_section.id,
            )
            self.assertEqual(
                about_and_notice_section["created_at"],
                expected.created_at.strftime(self.timestamp_format),
            )
            self.assertEqual(
                about_and_notice_section["updated_at"],
                expected.updated_at.strftime(self.timestamp_format),
            )

        self.assertTrue(self.user.has_accepted_latest_terms_of_service)
        self.assertTrue(self.user.has_accepted_latest_privacy_policy)

    def _assert_accept_fail(self, response: DRFResponse, expected_data: list):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(
            response.data,
            [{"non_field_errors": [self.error_messages[expected.type]]} for expected in expected_data],
        )

    def _before_accept_about_request(self, increase: Optional[int] = None):
        result = None
        if increase:
            about_section_3 = make(
                AboutAndNoticeSection,
                type=self.about_section_1.type,
                version=self.about_section_1.version + increase,
            )
            about_section_4 = make(
                AboutAndNoticeSection,
                type=self.about_section_2.type,
                version=self.about_section_2.version + increase,
            )
            result = [about_section_3, about_section_4]
        self.assertFalse(self.user.has_accepted_latest_terms_of_service)
        self.assertFalse(self.user.has_accepted_latest_privacy_policy)
        return result

    def test_about_list_authorized(self):
        expected_about_sections = [
            (self.about_section_1, self.about_translation_1),
            (self.about_section_2, self.about_translation_2),
        ]
        url = reverse("about-list")
        response = self.get(url)
        self._assert_list(response, expected_about_sections, status.HTTP_200_OK)

    def test_about_list_unauthorized(self):
        expected_about_sections = [
            (self.about_section_1, self.about_translation_1),
            (self.about_section_2, self.about_translation_2),
        ]
        url = reverse("about-list")
        response = self.client.get(url)
        self._assert_list(response, expected_about_sections, status.HTTP_200_OK)

    def test_about_list_authorized_higher_version(self):
        about_section_3 = make(
            AboutAndNoticeSection,
            type=self.about_section_1.type,
            version=self.about_section_1.version + 1,
        )
        about_translation_3 = make(AboutAndNoticeSectionTranslation, section=about_section_3)

        about_section_4 = make(
            AboutAndNoticeSection,
            type=self.about_section_2.type,
            version=self.about_section_2.version + 1,
        )
        about_translation_4 = make(AboutAndNoticeSectionTranslation, section=about_section_4)

        expected_about_sections = [
            (about_section_3, about_translation_3),
            (about_section_4, about_translation_4),
        ]

        url = reverse("about-list")
        response = self.get(url)
        self._assert_list(response, expected_about_sections, status.HTTP_200_OK)

    def test_about_list_authorized_higher_version_gap(self):
        about_section_3 = make(
            AboutAndNoticeSection,
            type=self.about_section_1.type,
            version=self.about_section_1.version + 2,
        )
        about_translation_3 = make(AboutAndNoticeSectionTranslation, section=about_section_3)

        about_section_4 = make(
            AboutAndNoticeSection,
            type=self.about_section_2.type,
            version=self.about_section_2.version + 2,
        )
        about_translation_4 = make(AboutAndNoticeSectionTranslation, section=about_section_4)

        expected_about_sections = [
            (about_section_3, about_translation_3),
            (about_section_4, about_translation_4),
        ]

        url = reverse("about-list")
        response = self.get(url)
        self._assert_list(response, expected_about_sections, status.HTTP_200_OK)

    def test_accept_about(self):
        self.query_limits["ANY POST REQUEST"] = 11
        self._before_accept_about_request()
        expected_about_sections = [self.about_section_1.id, self.about_section_2.id]
        response = self.authorize().post(
            self.accept_about_url,
            data=[self.about_section_1.id, self.about_section_2.id],
        )
        self._assert_accept_success(response, expected_about_sections)

    def test_accept_about_higher_version(self):
        self.query_limits["ANY POST REQUEST"] = 11
        about_section_3, about_section_4 = self._before_accept_about_request(1)
        expected_about_sections = [about_section_3.id, about_section_4.id]
        response = self.authorize().post(self.accept_about_url, data=[about_section_3.id, about_section_4.id])
        self._assert_accept_success(response, expected_about_sections)

    def test_accept_about_higher_version_gap(self):
        self.query_limits["ANY POST REQUEST"] = 11
        about_section_3, about_section_4 = self._before_accept_about_request(2)
        expected_about_sections = [about_section_3.id, about_section_4.id]
        response = self.authorize().post(self.accept_about_url, data=[about_section_3.id, about_section_4.id])
        self._assert_accept_success(response, expected_about_sections)

    def test_accept_about_lower_version(self):
        self.query_limits["ANY POST REQUEST"] = 9
        self._before_accept_about_request(1)
        expected_about_sections = [self.about_section_1, self.about_section_2]
        response = self.authorize().post(
            self.accept_about_url,
            data=[self.about_section_1.id, self.about_section_2.id],
        )
        self._assert_accept_fail(response, expected_about_sections)

    def test_accept_about_lower_version_gap(self):
        self.query_limits["ANY POST REQUEST"] = 9
        self._before_accept_about_request(2)
        expected_about_sections = [self.about_section_1, self.about_section_2]
        response = self.authorize().post(
            self.accept_about_url,
            data=[self.about_section_1.id, self.about_section_2.id],
        )
        self._assert_accept_fail(response, expected_about_sections)

    def test_about_detail_authorized(self):
        url = reverse("about-detail", kwargs={"pk": str(self.about_section_1.id)})
        response = self.get(url)
        self._assert_detail(
            response.data,
            self.about_section_1,
            self.about_translation_1,
            status.HTTP_200_OK,
        )

    def test_about_detail_unauthorized(self):
        url = reverse("about-detail", kwargs={"pk": str(self.about_section_1.id)})
        response = self.client.get(url)
        self._assert_detail(
            response.data,
            self.about_section_1,
            self.about_translation_1,
            status.HTTP_200_OK,
        )


class TestPushNotifications(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.devices = make(FCMDevice, _quantity=2, user=self.user, _fill_optional=True)

    def test_push_notifications_update_device(self):
        response = self.post(
            reverse("devices-list"),
            data={
                "name": "TestDevice",
                "registration_id": self.devices[0].registration_id,
                "device_id": self.devices[0].device_id,
                "active": True,
                "type": self.devices[0].type,
            },
        )
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.devices[0].refresh_from_db()
        self.assertEqual(self.devices[0].name, "TestDevice")

    def test_push_notifications_recreate_device(self):
        data = {
            "name": "TestDevice",
            "registration_id": self.devices[0].registration_id,
            "device_id": self.devices[0].device_id,
            "active": True,
            "type": self.devices[0].type,
        }
        self.devices[0].delete()
        response = self.post(
            reverse("devices-list"),
            data=data,
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertTrue(FCMDevice.objects.filter(registration_id=data["registration_id"]).exists())

    def test_delete_fcm_device_with_same_registration_id(self):
        logging.disable(logging.ERROR)
        device_id = "device_1"
        name = "Test Device"
        registration_id = "registration_id1"
        device_type = "android"
        make(
            FCMDevice,
            name=name,
            registration_id=registration_id,
            user=self.user,
            device_id=device_id,
            active=True,
            type=device_type,
            _quantity=2,
        )
        self.assertEqual(FCMDevice.objects.filter(registration_id=registration_id).count(), 2)
        response = self.delete(reverse("devices-detail", args=[registration_id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(FCMDevice.objects.filter(registration_id=registration_id).count(), 1)
        logging.disable(logging.NOTSET)


class DashboardOrderTests(BaseTestCase):
    def test_create_dashboard_order_with_duplicating_order_fields(self):
        dashboard_order = DashboardOrder(core_program=1, recipes=2, skin_tools=3, skin_school=4, skin_stories=4)
        self.assertRaises(ValidationError, dashboard_order.clean)


class MailChimpNewsLetterTestCase(BaseTestCase):
    @patch("requests.post")
    def test_news_letter(self, mock):
        response = Response()
        response.status_code = 403
        response._content = bytes(json.dumps({"title": "Member Exists"}), "utf-8")
        mock.return_value = response
        response = self.client.post(reverse("newsletter-subscribe"), data={"email": "test@test.com"})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code, response.data)
        self.assertEqual(response.json()["non_field_errors"], ["error_member_exists"])


class ReviewTests(BaseTestCase):
    url = "reviews"
    errors = {
        "not_found": "Not found.",
        "method_not_allowed": {
            method: f'Method "{method}" not allowed.' for method in ["POST", "PUT", "PATCH", "DELETE"]
        },
    }

    def setUp(self):
        super().setUp()
        self.review = make(Review)

    def get_url(self, *args: list[int]) -> str:
        suffix = "detail" if len(args) else "list"
        return reverse(f"{self.url}-{suffix}", args=args)

    def get_error_response(self, message: str) -> dict[str, str]:
        return {"detail": message}

    def check_error_response(self, response: DRFResponse, status_code: int, error_message: str) -> None:
        self.assertEqual(response.status_code, status_code, response.data)
        self.assertDictEqual(response.data, self.get_error_response(error_message))

    def check_method_not_allowed_error_response(self, response: DRFResponse, http_method: str) -> None:
        error_message = self.errors["method_not_allowed"][http_method]  # type: ignore
        self.check_error_response(response, status.HTTP_405_METHOD_NOT_ALLOWED, error_message)

    def check_response(self, review: dict[str, Union[int, str]], expected: Review):
        for attr in ["id", "username", "description", "rating"]:
            self.assertEqual(review.get(attr), getattr(expected, attr), attr)

    def test_review_list(self):
        review_2 = make(Review)
        review_3 = make(Review)
        expected_list = [review_3, review_2, self.review]

        response = self.client.get(self.get_url())

        self.assertEqual(status.HTTP_200_OK, response.status_code, response.data)
        for review, expected in zip(response.data["results"], expected_list):
            self.check_response(review, expected)

    def test_review_detail(self):
        response = self.client.get(self.get_url(self.review.id))
        self.assertEqual(status.HTTP_200_OK, response.status_code, response.data)
        self.check_response(response.data, self.review)

    def test_review_detail_non_existent(self):
        response = self.client.get(self.get_url(self.review.id + 1))
        self.check_error_response(response, status.HTTP_404_NOT_FOUND, self.errors["not_found"])

    def test_review_update(self):
        response = self.client.put(self.get_url(self.review.id))
        self.check_method_not_allowed_error_response(response, "PUT")

    def test_review_partial_update(self):
        response = self.client.patch(self.get_url(self.review.id))
        self.check_method_not_allowed_error_response(response, "PATCH")

    def test_review_delete(self):
        response = self.client.delete(self.get_url(self.review.id))
        self.check_method_not_allowed_error_response(response, "DELETE")

    def test_review_create(self):
        response = self.client.post(self.get_url())
        self.check_method_not_allowed_error_response(response, "POST")


class GlobalVariablesTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.review = make(GlobalVariables, indian_paywall=True)

    def test_review_list(self):
        result = self.authorize().get(reverse("global_variables"))
        expected_result = {"indian_paywall": True}
        self.assertEqual(result.data, expected_result)
