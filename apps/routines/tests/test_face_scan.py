from contextlib import contextmanager
import datetime
import io
import json
from typing import Tuple
from unittest.mock import patch
from urllib.parse import urlencode
import uuid

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message
from freezegun import freeze_time
from model_bakery.baker import make
from parameterized import parameterized
from PIL import Image
from rest_framework import status

from apps.home.models import (
    SiteConfiguration,
    NotificationTemplate,
    NotificationTemplateTranslation,
    FaceScanCommentTemplate,
    FaceScanCommentTemplateTranslation,
)
from apps.questionnaire.models import UserQuestionnaire
from apps.routines import FaceScanNotificationTypes, PurchaseStatus
from apps.routines.models import (
    FaceScan,
    FaceScanSmoothingAnalytics,
    FaceScanAnalytics,
    FaceScanComment,
    StatisticsPurchase,
)
from apps.routines.tasks import (
    send_reminder_for_face_scans,
    generate_reminder_message,
)
from apps.users.models import UserSettings
from apps.utils.tasks import (
    _generate_message_from_translation,
    PUSH_NOTIFICATION_TYPE_TO_CLICK_ACTION_LINK,
)
from apps.utils.tests_utils import BaseTestCase


class BaseFaceScanTests(BaseTestCase):
    def _upload_picture_side_effect(
        self, subject_id: str, image_base64: str, company_id: str, token: str
    ) -> Tuple[str, str]:
        return str(uuid.uuid4()), str(uuid.uuid4())

    def setUp(self):
        super().setUp()

        self.patcher_get_subject = patch("apps.routines.signals.get_subject_id")
        self.mock_haut_ai_get_subject_id = self.patcher_get_subject.start()
        self.mock_haut_ai_get_subject_id.return_value = "12312"
        self.addCleanup(self.patcher_get_subject.stop)

        self.patcher_upload_picture = patch("apps.routines.signals.upload_picture")
        self.mock_haut_ai_get_subject_id_upload_picture = self.patcher_upload_picture.start()
        self.mock_haut_ai_get_subject_id_upload_picture.side_effect = self._upload_picture_side_effect
        self.addCleanup(self.patcher_upload_picture.stop)

        self.patcher_get_auth_info = patch("apps.routines.signals.get_auth_info")
        self.mock_haut_ai_get_auth_info = self.patcher_get_auth_info.start()
        self.mock_haut_ai_get_auth_info.return_value = "1234", "4321"
        self.addCleanup(self.patcher_get_auth_info.stop)

        self.image = SimpleUploadedFile("icon.png", b"file_content")

        self.face_scan_1 = make(FaceScan, user=self.user, image=self.image)
        self.face_scan_1.save()

        self.face_scan_2 = make(FaceScan, user=self.user, image=self.image)
        self.face_scan_2.save()

        self.invalid_template = make(NotificationTemplate, name="invalid face scan template")
        self.invalid_template_translation = make(
            NotificationTemplateTranslation,
            template=self.invalid_template,
            language=self.user.language,
        )

        self.valid_template = make(NotificationTemplate, name="face scan completed template")
        self.valid_template_translation = make(
            NotificationTemplateTranslation,
            template=self.valid_template,
            language=self.user.language,
        )

        self.site_config = SiteConfiguration.get_solo()
        self.site_config.invalid_face_scan_notification_template = self.invalid_template
        self.site_config.face_analysis_completed_notification_template = self.valid_template
        self.site_config.save()

        self.devices = make(FCMDevice, user=self.user, _quantity=2)


class FaceScanTests(BaseFaceScanTests):
    def generate_image(self):
        generated_file = io.BytesIO()
        image = Image.new("RGBA", size=(100, 100), color=(155, 0, 0))
        image.save(generated_file, "png")
        generated_file.name = "test.png"
        generated_file.seek(0)
        return generated_file

    def test_create_face_scan_object(self):
        url = reverse("face_scans-list")
        image = self.generate_image()
        data = {"image": image}

        response = self.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FaceScan.objects.count(), 3)

    def test_face_scan_list(self):
        url = reverse("face_scans-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_face_scan_1 = response.json()["results"][0]
        response_face_scan_2 = response.json()["results"][1]

        self.assertEqual(response_face_scan_1["id"], self.face_scan_1.id)
        self.assertEqual(
            response_face_scan_1["created_at"],
            self.face_scan_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertIn(self.face_scan_1.image.url, response_face_scan_1["image"])

        self.assertEqual(response_face_scan_2["id"], self.face_scan_2.id)
        self.assertEqual(
            response_face_scan_2["created_at"],
            self.face_scan_2.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertIn(self.face_scan_2.image.url, response_face_scan_2["image"])

    def test_bulk_delete_face_scan(self):
        self.query_limits["ANY DELETE REQUEST"] = 11
        self.assertEqual(FaceScan.objects.count(), 2)
        url = reverse("face_scans-bulk-delete")
        data = {"del_list": [1, 2]}
        response = self.delete(url, data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(FaceScan.objects.count(), 0)

    def test_face_scan_returns_non_if_no_face_scan_exist(self):
        self.face_scan_1.delete()
        self.face_scan_2.delete()
        url = reverse("face_scans-latest-scan")
        response = self.get(url)
        self.assertEqual(response.json()["latest_scan"], None)
        self.assertEqual(response.json()["is_processed"], False)

    def test_latest_face_scan_is_in_progress(self):
        face_scan = make(FaceScan, user=self.user)
        url = reverse("face_scans-latest-scan")
        response = self.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["latest_scan"],
            face_scan.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertFalse(response.json()["is_processed"])

    def test_latest_face_scan_with_analytics(self):
        face_scan1 = make(FaceScan, user=self.user)
        make(FaceScanAnalytics, face_scan=face_scan1, is_valid=True)
        face_scan2 = make(FaceScan, user=self.user)
        make(FaceScanAnalytics, face_scan=face_scan2, is_valid=False)
        # only face scan with valid analytics will be considered as latest face scan
        latest_face_scan = face_scan1
        url = reverse("face_scans-latest-scan")
        response = self.get(url)
        self.assertEqual(
            response.json()["latest_scan"],
            latest_face_scan.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["is_processed"], True)

    def test_create_face_scan_and_check_signal_trigger(self):
        url = reverse("face_scans-list")
        image = self.generate_image()
        data = {"image": image}

        response = self.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.mock_haut_ai_get_subject_id.called)
        self.assertTrue(self.mock_haut_ai_get_subject_id_upload_picture.called)

    @patch("apps.routines.views.get_smoothing_results")
    @patch("apps.routines.views.get_image_results")
    @patch("apps.routines.views.generate_and_send_notification", autospec=True)
    @patch("apps.routines.views.get_auth_info", return_value=["1234", "4321"])
    def test_haut_ai_webhook_trigger(
        self,
        get_auth_info_mock,
        notification_task,
        get_image_results_mock,
        get_smoothing_results_mock,
    ):
        self.query_limits["ANY POST REQUEST"] = 10
        with open("apps/routines/test_files/smoothing_results.json", "r") as smoothing_data_file:
            smoothing_data = json.load(smoothing_data_file)

        with open("apps/routines/test_files/image_results.json", "r") as image_file_data:
            image_data = json.load(image_file_data)

        get_smoothing_results_mock.return_value = smoothing_data
        get_image_results_mock.return_value = image_data

        webhook_data = {
            "event": "photo_calculated_by_app",
            "image_id": self.face_scan_2.haut_ai_image_id,
            "batch_id": self.face_scan_2.haut_ai_batch_id,
            "subject_id": self.face_scan_2.user.haut_ai_subject_id,
            "subject_name": "Test",
            "dataset_id": settings.HAUT_AI_DATA_SET_ID,
            "company_id": "6f8c2134-ffba-491a-b1a6-1b897b42d936",
            "application_name": "Face Skin Metrics 2.0",
            "application_run_id": "f546e0ee-be44-4597-9992-47fe7939eafe",
        }
        url = reverse("face_scans-webhook")
        query_params = {"auth_key": settings.HAUT_AI_AUTH_KEY}
        response = self.post(f"{url}?{urlencode(query_params)}", webhook_data)

        self.face_scan_2.refresh_from_db()
        self.assertIsNotNone(self.face_scan_2.analytics)
        self.assertIsNotNone(self.face_scan_2.smoothing_analytics)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertTrue(self.site_config)
        self.assertTrue(self.site_config.invalid_face_scan_notification_template)
        self.assertEqual(
            self.site_config.invalid_face_scan_notification_template,
            self.invalid_template,
        )
        self.assertTrue(self.site_config.face_analysis_completed_notification_template)
        self.assertEqual(
            self.site_config.face_analysis_completed_notification_template,
            self.valid_template,
        )
        notification_task.delay.assert_called_with(
            self.valid_template.id,
            FaceScanNotificationTypes.SUCCESS,
            self.valid_template_translation.language.pk,
            [device.id for device in self.devices],
        )

    @patch("apps.routines.views.get_smoothing_results")
    @patch("apps.routines.views.get_image_results")
    @patch("apps.routines.views.generate_and_send_notification", autospec=True)
    @patch("apps.routines.views.get_auth_info", return_value=["1234", "4321"])
    def test_haut_ai_webhook_trigger_save_data(
        self,
        get_auth_info_mock,
        notification_task,
        get_image_results_mock,
        get_smoothing_results_mock,
    ):
        self.query_limits["ANY POST REQUEST"] = 10
        with open("apps/routines/test_files/smoothing_results.json", "r") as smoothing_data_file:
            smoothing_data = json.load(smoothing_data_file)

        with open("apps/routines/test_files/image_results.json", "r") as image_file_data:
            image_data = json.load(image_file_data)

        get_smoothing_results_mock.return_value = smoothing_data
        get_image_results_mock.return_value = image_data

        webhook_data = {
            "event": "photo_calculated_by_app",
            "image_id": self.face_scan_2.haut_ai_image_id,
            "batch_id": self.face_scan_2.haut_ai_batch_id,
            "subject_id": self.face_scan_2.user.haut_ai_subject_id,
            "subject_name": "Test",
            "dataset_id": settings.HAUT_AI_DATA_SET_ID,
            "company_id": "6f8c2134-ffba-491a-b1a6-1b897b42d936",
            "application_name": "Face Skin Metrics 2.0",
            "application_run_id": "f546e0ee-be44-4597-9992-47fe7939eafe",
        }
        url = reverse("face_scans-webhook")
        query_params = {"auth_key": settings.HAUT_AI_AUTH_KEY}
        response = self.post(f"{url}?{urlencode(query_params)}", webhook_data)

        self.face_scan_2.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        notification_task.delay.assert_called_with(
            self.valid_template.id,
            FaceScanNotificationTypes.SUCCESS,
            self.valid_template_translation.language.pk,
            [device.id for device in self.devices],
        )

        smoothing_analytics = FaceScanSmoothingAnalytics.objects.get(face_scan=self.face_scan_2)
        self.assertEqual(smoothing_analytics.acne, 99)
        self.assertEqual(smoothing_analytics.lines, 64)
        self.assertEqual(smoothing_analytics.wrinkles, 0)
        self.assertEqual(smoothing_analytics.pigmentation, 86)
        self.assertEqual(smoothing_analytics.translucency, 59)
        self.assertEqual(smoothing_analytics.quality, 54)
        self.assertEqual(smoothing_analytics.eye_bags, 73)
        self.assertEqual(smoothing_analytics.pores, 30)
        self.assertEqual(smoothing_analytics.sagging, 40)
        self.assertEqual(smoothing_analytics.uniformness, 43)
        self.assertEqual(smoothing_analytics.hydration, 75)
        self.assertEqual(smoothing_analytics.redness, 70)

        analytics = FaceScanAnalytics.objects.get(face_scan=self.face_scan_2)
        self.assertEqual(analytics.acne, 99)
        self.assertEqual(analytics.lines, 64)
        self.assertEqual(analytics.wrinkles, 0)
        self.assertEqual(analytics.pigmentation, 86)
        self.assertEqual(analytics.translucency, 59)
        self.assertEqual(analytics.quality, 54)
        self.assertEqual(analytics.eye_bags, 73)
        self.assertEqual(analytics.pores, 30)
        self.assertEqual(analytics.sagging, 40)
        self.assertEqual(analytics.uniformness, 43)
        self.assertEqual(analytics.hydration, 75)
        self.assertEqual(analytics.redness, 70)

    @patch("apps.routines.views.get_smoothing_results")
    @patch("apps.routines.views.get_image_results")
    @patch("apps.routines.views.generate_and_send_notification", autospec=True)
    @patch("apps.routines.views.get_auth_info", return_value=["1234", "4321"])
    def test_haut_ai_webhook_trigger_save_data_no_face(
        self,
        get_auth_info_mock,
        notification_task,
        get_image_results_mock,
        get_smoothing_results_mock,
    ):
        self.query_limits["ANY POST REQUEST"] = 10
        with open("apps/routines/test_files/smoothing_results_no_face.json", "r") as smoothing_data_file:
            smoothing_data = json.load(smoothing_data_file)

        with open("apps/routines/test_files/image_results_no_face.json", "r") as image_file_data:
            image_data = json.load(image_file_data)

        get_smoothing_results_mock.return_value = smoothing_data
        get_image_results_mock.return_value = image_data

        webhook_data = {
            "event": "photo_calculated_by_app",
            "image_id": self.face_scan_2.haut_ai_image_id,
            "batch_id": self.face_scan_2.haut_ai_batch_id,
            "subject_id": self.face_scan_2.user.haut_ai_subject_id,
            "subject_name": "Test",
            "dataset_id": settings.HAUT_AI_DATA_SET_ID,
            "company_id": "6f8c2134-ffba-491a-b1a6-1b897b42d936",
            "application_name": "Face Skin Metrics 2.0",
            "application_run_id": "f546e0ee-be44-4597-9992-47fe7939eafe",
        }
        url = reverse("face_scans-webhook")
        query_params = {"auth_key": settings.HAUT_AI_AUTH_KEY}
        response = self.post(f"{url}?{urlencode(query_params)}", webhook_data)

        self.face_scan_2.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        notification_task.delay.assert_called_with(
            self.invalid_template.id,
            FaceScanNotificationTypes.INVALID,
            self.valid_template_translation.language.pk,
            [device.id for device in self.devices],
        )

        smoothing_analytics = FaceScanSmoothingAnalytics.objects.get(face_scan=self.face_scan_2)
        self.assertEqual(smoothing_analytics.acne, 0)
        self.assertEqual(smoothing_analytics.lines, 0)
        self.assertEqual(smoothing_analytics.wrinkles, 0)
        self.assertEqual(smoothing_analytics.pigmentation, 0)
        self.assertEqual(smoothing_analytics.translucency, 0)
        self.assertEqual(smoothing_analytics.quality, 0)
        self.assertEqual(smoothing_analytics.eye_bags, 0)
        self.assertEqual(smoothing_analytics.pores, 0)
        self.assertEqual(smoothing_analytics.sagging, 0)
        self.assertEqual(smoothing_analytics.uniformness, 0)
        self.assertEqual(smoothing_analytics.hydration, 0)
        self.assertEqual(smoothing_analytics.redness, 0)

        analytics = FaceScanAnalytics.objects.get(face_scan=self.face_scan_2)
        self.assertEqual(analytics.acne, 0)
        self.assertEqual(analytics.lines, 0)
        self.assertEqual(analytics.wrinkles, 0)
        self.assertEqual(analytics.pigmentation, 0)
        self.assertEqual(analytics.translucency, 0)
        self.assertEqual(analytics.quality, 0)
        self.assertEqual(analytics.eye_bags, 0)
        self.assertEqual(analytics.pores, 0)
        self.assertEqual(analytics.sagging, 0)
        self.assertEqual(analytics.uniformness, 0)
        self.assertEqual(analytics.hydration, 0)
        self.assertEqual(analytics.redness, 0)
        self.assertEqual(analytics.is_valid, False)

    @patch("apps.routines.views.get_smoothing_results")
    @patch("apps.routines.views.get_image_results")
    @patch("apps.routines.views.generate_and_send_notification", autospec=True)
    @patch("apps.routines.views.get_auth_info", return_value=["1234", "4321"])
    def test_haut_ai_webhook_trigger_for_duplicate_face_analytics_data(
        self,
        get_auth_info_mock,
        notification_task,
        get_image_results_mock,
        get_smoothing_results_mock,
    ):
        self.query_limits["ANY POST REQUEST"] = 10
        with open("apps/routines/test_files/smoothing_results.json", "r") as smoothing_data_file:
            smoothing_data = json.load(smoothing_data_file)

        with open("apps/routines/test_files/image_results.json", "r") as image_file_data:
            image_data = json.load(image_file_data)

        get_smoothing_results_mock.return_value = smoothing_data
        get_image_results_mock.return_value = image_data

        webhook_data = {
            "event": "photo_calculated_by_app",
            "image_id": self.face_scan_2.haut_ai_image_id,
            "batch_id": self.face_scan_2.haut_ai_batch_id,
            "subject_id": self.face_scan_2.user.haut_ai_subject_id,
            "subject_name": "Test",
            "dataset_id": settings.HAUT_AI_DATA_SET_ID,
            "company_id": "6f8c2134-ffba-491a-b1a6-1b897b42d936",
            "application_name": "Face Skin Metrics 2.0",
            "application_run_id": "f546e0ee-be44-4597-9992-47fe7939eafe",
        }
        url = reverse("face_scans-webhook")
        query_params = {"auth_key": settings.HAUT_AI_AUTH_KEY}
        response = self.post(f"{url}?{urlencode(query_params)}", webhook_data)

        self.face_scan_2.refresh_from_db()
        self.assertIsNotNone(self.face_scan_2.analytics)
        self.assertIsNotNone(self.face_scan_2.smoothing_analytics)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertTrue(self.site_config)
        self.assertTrue(self.site_config.invalid_face_scan_notification_template)
        self.assertEqual(
            self.site_config.invalid_face_scan_notification_template,
            self.invalid_template,
        )
        self.assertTrue(self.site_config.face_analysis_completed_notification_template)
        self.assertEqual(
            self.site_config.face_analysis_completed_notification_template,
            self.valid_template,
        )
        notification_task.delay.assert_called_with(
            self.valid_template.id,
            FaceScanNotificationTypes.SUCCESS,
            self.valid_template_translation.language.pk,
            [device.id for device in self.devices],
        )
        with self.assertNotRaises(IntegrityError):
            response2 = self.post(f"{url}?{urlencode(query_params)}", webhook_data)
            self.assertEqual(response2.status_code, status.HTTP_204_NO_CONTENT)

    @contextmanager
    def assertNotRaises(self, exc_type):  # noqa: N802
        try:
            yield None
        except exc_type:
            raise self.failureException("{} raised".format(exc_type.__name__))

    def test_notification_message_for_face_analysis_complete(self):
        message = _generate_message_from_translation(self.valid_template_translation, FaceScanNotificationTypes.SUCCESS)
        self.assertTrue(message)
        self.assertEqual(
            message.data["link"],
            PUSH_NOTIFICATION_TYPE_TO_CLICK_ACTION_LINK[FaceScanNotificationTypes.SUCCESS],
        )
        self.assertEqual(message.data["type"], "face_scan")
        self.assertEqual(message.notification.title, self.valid_template_translation.title)
        self.assertEqual(message.notification.body, self.valid_template_translation.body)

    def test_notification_message_for_invalid_face_scan(self):
        message = _generate_message_from_translation(
            self.invalid_template_translation, FaceScanNotificationTypes.INVALID
        )
        self.assertTrue(message)
        self.assertEqual(
            message.data["link"],
            PUSH_NOTIFICATION_TYPE_TO_CLICK_ACTION_LINK[FaceScanNotificationTypes.INVALID],
        )
        self.assertEqual(message.data["type"], "face_scan")
        self.assertEqual(message.notification.title, self.invalid_template_translation.title)
        self.assertEqual(message.notification.body, self.invalid_template_translation.body)


class FaceScanAvailabilityTests(BaseFaceScanTests):
    @freeze_time("2022-09-30 13:00:00")
    def test_face_scan_available_for_premium_user(self):
        statistics_purchase = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            user=self.user,
        )
        statistics_purchase.status = PurchaseStatus.COMPLETED.value
        statistics_purchase.save(is_verified=True)
        current_time = timezone.now()
        self.face_scan_1.created_at = current_time - datetime.timedelta(days=1)
        self.face_scan_2.created_at = current_time - datetime.timedelta(days=2)
        self.face_scan_1.save()
        self.face_scan_2.save()
        make(FaceScanAnalytics, face_scan=self.face_scan_1, is_valid=True)
        make(FaceScanAnalytics, face_scan=self.face_scan_2, is_valid=True)

        url = reverse("face_scans-availability")
        response = self.get(url)

        self.assertEqual(response.status_code, 204)

    @freeze_time("2022-09-30 13:00:00")
    def test_face_scan_available_for_premium_user_disregarding_invalid_face_scans(self):
        statistics_purchase = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            user=self.user,
        )
        statistics_purchase.status = PurchaseStatus.COMPLETED.value
        statistics_purchase.save(is_verified=True)
        make(FaceScanAnalytics, face_scan=self.face_scan_1, is_valid=False)
        make(FaceScanAnalytics, face_scan=self.face_scan_2, is_valid=False)

        url = reverse("face_scans-availability")
        response = self.get(url)

        self.assertEqual(response.status_code, 204)

    @freeze_time("2022-09-30 13:00:00")
    def test_face_scan_available_for_expired_but_still_premium_user(self):
        make(
            StatisticsPurchase,
            status=PurchaseStatus.EXPIRED.value,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            user=self.user,
        )
        current_time = timezone.now()
        self.face_scan_1.created_at = current_time - datetime.timedelta(days=1)
        self.face_scan_2.created_at = current_time - datetime.timedelta(days=2)
        self.face_scan_1.save()
        self.face_scan_2.save()
        make(FaceScanAnalytics, face_scan=self.face_scan_1, is_valid=True)
        make(FaceScanAnalytics, face_scan=self.face_scan_2, is_valid=True)

        url = reverse("face_scans-availability")
        response = self.get(url)

        self.assertEqual(response.status_code, 204)

    @freeze_time("2022-09-30 13:00:00")
    def test_face_scan_unavailable_for_premium_user(self):
        statistics_purchase = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            user=self.user,
        )
        statistics_purchase.status = PurchaseStatus.COMPLETED.value
        statistics_purchase.save(is_verified=True)
        current_time = timezone.now()
        self.face_scan_1.created_at = current_time
        self.face_scan_2.created_at = current_time - datetime.timedelta(days=1)
        make(FaceScanAnalytics, face_scan=self.face_scan_1, is_valid=True)
        make(FaceScanAnalytics, face_scan=self.face_scan_2, is_valid=True)
        self.face_scan_1.save()
        self.face_scan_2.save()

        url = reverse("face_scans-availability")
        response = self.get(url)

        self.assertEqual(response.status_code, 400)

    def test_face_scan_available_for_regular_user(self):
        current_time = timezone.now()
        self.face_scan_1.created_at = current_time - datetime.timedelta(days=3)
        self.face_scan_2.created_at = current_time - datetime.timedelta(days=6)
        self.face_scan_1.save()
        self.face_scan_2.save()
        make(FaceScanAnalytics, face_scan=self.face_scan_1, is_valid=True)
        make(FaceScanAnalytics, face_scan=self.face_scan_2, is_valid=True)

        url = reverse("face_scans-availability")
        response = self.get(url)

        self.assertEqual(response.status_code, 204)

    def test_face_scan_unavailable_for_regular_user(self):
        current_time = timezone.now()
        self.face_scan_1.created_at = current_time
        self.face_scan_2.created_at = current_time - datetime.timedelta(days=3)
        self.face_scan_1.save()
        self.face_scan_2.save()
        make(FaceScanAnalytics, face_scan=self.face_scan_1, is_valid=True)
        make(FaceScanAnalytics, face_scan=self.face_scan_2, is_valid=True)

        url = reverse("face_scans-availability")
        response = self.get(url)

        self.assertEqual(response.status_code, 400)


class FaceScanSmoothingAnalyticsTests(BaseFaceScanTests):
    def setUp(self):
        super().setUp()
        make(FaceScanAnalytics, face_scan=self.face_scan_1, is_valid=True)
        make(FaceScanAnalytics, face_scan=self.face_scan_2, is_valid=True)
        self.face_scan_1_smoothing_analytics = make(FaceScanSmoothingAnalytics, face_scan=self.face_scan_1)
        self.face_scan_1_smoothing_analytics.save()

        self.face_scan_2_smoothing_analytics = make(FaceScanSmoothingAnalytics, face_scan=self.face_scan_2)
        self.face_scan_2_smoothing_analytics.save()

        image = SimpleUploadedFile("icon.png", b"file_content")
        face_scan_3 = make(FaceScan, user=self.user, image=image)
        make(FaceScanAnalytics, face_scan=face_scan_3, is_valid=False)
        make(FaceScanSmoothingAnalytics, face_scan=face_scan_3)

    def test_face_scan_analytics_list(self):
        url = reverse("face_scan_smoothing_analytics-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.json()["results"]), 2)

        response_face_scan_1 = response.json()["results"][0]
        response_face_scan_2 = response.json()["results"][1]

        self.assertEqual(
            response_face_scan_2["created_at"],
            self.face_scan_1_smoothing_analytics.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )

        self.assertEqual(response_face_scan_2["acne"], self.face_scan_1_smoothing_analytics.acne)

        self.assertEqual(response_face_scan_2["lines"], self.face_scan_1_smoothing_analytics.lines)
        self.assertEqual(
            response_face_scan_2["wrinkles"],
            self.face_scan_1_smoothing_analytics.wrinkles,
        )
        self.assertEqual(
            response_face_scan_2["pigmentation"],
            self.face_scan_1_smoothing_analytics.pigmentation,
        )
        self.assertEqual(
            response_face_scan_2["translucency"],
            self.face_scan_1_smoothing_analytics.translucency,
        )
        self.assertEqual(
            response_face_scan_2["quality"],
            self.face_scan_1_smoothing_analytics.quality,
        )
        self.assertEqual(
            response_face_scan_2["eye_bags"],
            self.face_scan_1_smoothing_analytics.eye_bags,
        )
        self.assertEqual(response_face_scan_2["pores"], self.face_scan_1_smoothing_analytics.pores)

        self.assertEqual(
            response_face_scan_2["sagging"],
            self.face_scan_1_smoothing_analytics.sagging,
        )

        self.assertEqual(
            response_face_scan_2["uniformness"],
            self.face_scan_1_smoothing_analytics.uniformness,
        )

        self.assertEqual(
            response_face_scan_2["hydration"],
            self.face_scan_1_smoothing_analytics.hydration,
        )

        self.assertEqual(
            response_face_scan_2["redness"],
            self.face_scan_1_smoothing_analytics.redness,
        )

        self.assertEqual(
            response_face_scan_1["created_at"],
            self.face_scan_2_smoothing_analytics.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )


class FaceScanAnalyticsTests(BaseFaceScanTests):
    def setUp(self):
        super().setUp()

        self.face_scan_1_analytics = make(FaceScanAnalytics, face_scan=self.face_scan_1)
        self.face_scan_1_analytics.save()

        self.face_scan_2_analytics = make(FaceScanAnalytics, face_scan=self.face_scan_2)
        self.face_scan_2_analytics.save()

        image = SimpleUploadedFile("icon.png", b"file_content")
        face_scan_3 = make(FaceScan, user=self.user, image=image)
        make(FaceScanAnalytics, face_scan=face_scan_3, is_valid=False)

    def test_face_scan_analytics_list(self):
        url = reverse("face_scan_analytics-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 2)

        response_face_scan_1 = response.json()["results"][0]
        response_face_scan_2 = response.json()["results"][1]

        self.assertEqual(
            response_face_scan_2["created_at"],
            self.face_scan_1_analytics.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )

        self.assertEqual(response_face_scan_2["acne"], self.face_scan_1_analytics.acne)

        self.assertEqual(response_face_scan_2["lines"], self.face_scan_1_analytics.lines)
        self.assertEqual(response_face_scan_2["wrinkles"], self.face_scan_1_analytics.wrinkles)
        self.assertEqual(
            response_face_scan_2["pigmentation"],
            self.face_scan_1_analytics.pigmentation,
        )
        self.assertEqual(
            response_face_scan_2["translucency"],
            self.face_scan_1_analytics.translucency,
        )
        self.assertEqual(response_face_scan_2["quality"], self.face_scan_1_analytics.quality)
        self.assertEqual(response_face_scan_2["eye_bags"], self.face_scan_1_analytics.eye_bags)
        self.assertEqual(response_face_scan_2["pores"], self.face_scan_1_analytics.pores)

        self.assertEqual(response_face_scan_2["sagging"], self.face_scan_1_analytics.sagging)

        self.assertEqual(response_face_scan_2["uniformness"], self.face_scan_1_analytics.uniformness)

        self.assertEqual(response_face_scan_2["hydration"], self.face_scan_1_analytics.hydration)

        self.assertEqual(response_face_scan_2["redness"], self.face_scan_1_analytics.redness)

        self.assertEqual(
            response_face_scan_1["created_at"],
            self.face_scan_2_analytics.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )


class FaceScanCommentTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.face_scan = make(FaceScan, user=self.user)
        self.comment_template = make(FaceScanCommentTemplate)

    def test_face_scan_comment_list_without_translation(self):
        face_scan_comment = make(
            FaceScanComment,
            face_scan=self.face_scan,
            comment_template=self.comment_template,
        )
        url = reverse("face-scan-comments-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comments = response.json()["results"]
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]["id"], face_scan_comment.id)
        self.assertEqual(comments[0]["comment"], self.comment_template.name)
        self.assertEqual(comments[0]["face_scan"], self.face_scan.id)
        self.assertEqual(
            comments[0]["created_at"],
            face_scan_comment.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )

    def test_face_scan_comment_list_with_translation(self):
        translation = make(FaceScanCommentTemplateTranslation, template=self.comment_template)
        face_scan_comment = make(
            FaceScanComment,
            face_scan=self.face_scan,
            comment_template=self.comment_template,
        )
        url = reverse("face-scan-comments-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comments = response.json()["results"]
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]["id"], face_scan_comment.id)
        self.assertEqual(comments[0]["comment"], translation.body)
        self.assertEqual(comments[0]["face_scan"], self.face_scan.id)
        self.assertEqual(
            comments[0]["created_at"],
            face_scan_comment.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )


class FaceScanNotificationTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.user_settings = make(UserSettings, user=self.user, is_face_scan_reminder_active=True)
        patcher = patch("apps.routines.tasks.send_push_notifications")
        self.mocked_send_push_notifications = patcher.start()
        self.addCleanup(patcher.stop)
        self.face_scan_reminder_template = make(NotificationTemplate, name="Face Scan Reminder")
        self.face_scan_reminder_template_translation = make(
            NotificationTemplateTranslation,
            template=self.face_scan_reminder_template,
            language=self.user.language,
            title="Face Scan Reminder",
            body="You are skipping face scans for at least 72 hours.",
        )

        self.site_config = SiteConfiguration.get_solo()
        self.site_config.face_scan_reminder_notification_template = self.face_scan_reminder_template
        self.site_config.save()

    def test_generate_face_scan_reminder_message(self):
        generated_message = generate_reminder_message(self.face_scan_reminder_template_translation)
        self.assertIsInstance(generated_message, Message)
        self.assertEqual(
            generated_message.notification.title,
            self.face_scan_reminder_template_translation.title,
        )
        self.assertEqual(
            generated_message.notification.body,
            self.face_scan_reminder_template_translation.body,
        )

    @parameterized.expand(
        [
            [datetime.datetime(year=2022, month=6, day=2, hour=6)],
            [datetime.datetime(year=2022, month=6, day=5, hour=6)],
        ]
    )
    @freeze_time("2022-06-8 06:00:00")
    def test_face_scan_reminder_task_with_valid_timeline(self, last_face_scan_date):
        make(UserQuestionnaire, user=self.user)

        face_scan = make(FaceScan, user=self.user)
        face_scan.created_at = last_face_scan_date
        face_scan.save()

        face_scan_analytics = make(FaceScanAnalytics, face_scan=face_scan, is_valid=True)
        face_scan_analytics.created_at = last_face_scan_date
        face_scan_analytics.save()

        make(FCMDevice, user=self.user)
        generated_message = generate_reminder_message(self.face_scan_reminder_template_translation)
        send_reminder_for_face_scans()
        user_devices = FCMDevice.objects.filter(user=self.user)
        self.assertTrue(self.mocked_send_push_notifications.called)
        self.assertEqual(
            self.mocked_send_push_notifications.call_args.args[0].count(),
            user_devices.count(),
        )
        self.assertEqual(
            self.mocked_send_push_notifications.call_args.args[0].first(),
            user_devices.first(),
        )
        message = self.mocked_send_push_notifications.call_args.kwargs["message"]
        self.assertEqual(message.notification.title, generated_message.notification.title)
        self.assertEqual(message.notification.body, generated_message.notification.body)

    @parameterized.expand(
        [
            [datetime.datetime(year=2022, month=6, day=2, hour=6)],
            [datetime.datetime(year=2022, month=6, day=5, hour=6)],
        ]
    )
    @freeze_time("2022-06-8 06:00:00")
    def test_face_scan_reminder_task_with_valid_timeline_no_questionnaire(self, last_face_scan_date):
        face_scan = make(FaceScan, user=self.user)
        face_scan.created_at = last_face_scan_date
        face_scan.save()

        face_scan_analytics = make(FaceScanAnalytics, face_scan=face_scan, is_valid=True)
        face_scan_analytics.created_at = last_face_scan_date
        face_scan_analytics.save()

        make(FCMDevice, user=self.user)
        send_reminder_for_face_scans()
        self.assertFalse(self.mocked_send_push_notifications.called)

    @parameterized.expand(
        [
            [datetime.datetime(year=2022, month=6, day=2, hour=6)],
            [datetime.datetime(year=2022, month=6, day=3, hour=6)],
        ]
    )
    @freeze_time("2022-06-3 06:00:00")
    def test_face_scan_reminder_task_with_invalid_timeline(self, last_face_scan_date):
        face_scan = make(FaceScan, user=self.user)
        face_scan.created_at = last_face_scan_date
        face_scan.save()

        face_scan_analytics = make(FaceScanAnalytics, face_scan=face_scan, is_valid=True)
        face_scan_analytics.created_at = last_face_scan_date
        face_scan_analytics.save()

        make(FCMDevice, user=self.user)
        send_reminder_for_face_scans()
        FCMDevice.objects.filter(user=self.user)
        self.assertFalse(self.mocked_send_push_notifications.called)

    @parameterized.expand(
        [
            [datetime.datetime(year=2022, month=6, day=3, hour=6)],
            [datetime.datetime(year=2022, month=6, day=5, hour=6)],
        ]
    )
    @freeze_time("2022-06-8 06:00:00")
    def test_face_scan_reminder_task_with_valid_timeline_and_no_template(self, last_face_scan_date):
        self.site_config.face_scan_reminder_notification_template = None
        self.site_config.save()
        face_scan = make(FaceScan, user=self.user)
        face_scan.created_at = last_face_scan_date
        face_scan.save()

        face_scan_analytics = make(FaceScanAnalytics, face_scan=face_scan, is_valid=True)
        face_scan_analytics.created_at = last_face_scan_date
        face_scan_analytics.save()

        make(FCMDevice, user=self.user)
        send_reminder_for_face_scans()
        FCMDevice.objects.filter(user=self.user)
        self.assertFalse(self.mocked_send_push_notifications.called)

    @parameterized.expand(
        [
            [datetime.datetime(year=2022, month=6, day=3, hour=6)],
            [datetime.datetime(year=2022, month=6, day=5, hour=6)],
        ]
    )
    @freeze_time("2022-06-8 06:00:00")
    def test_face_scan_reminder_task_with_valid_timeline_but_reminder_disabled(self, last_face_scan_date):
        self.user_settings.is_face_scan_reminder_active = False
        self.user_settings.save()
        face_scan = make(FaceScan, user=self.user)
        face_scan.created_at = last_face_scan_date
        face_scan.save()

        face_scan_analytics = make(FaceScanAnalytics, face_scan=face_scan, is_valid=True)
        face_scan_analytics.created_at = last_face_scan_date
        face_scan_analytics.save()

        make(FCMDevice, user=self.user)
        send_reminder_for_face_scans()
        FCMDevice.objects.filter(user=self.user)
        self.assertFalse(self.mocked_send_push_notifications.called)

    @freeze_time("2022-06-8 06:00:00")
    def test_face_scan_reminder_task_with_valid_timeline_and_specified_users(self):
        make(UserQuestionnaire, user=self.user)
        make(FCMDevice, user=self.user)
        generated_message = generate_reminder_message(self.face_scan_reminder_template_translation)
        send_reminder_for_face_scans([self.user.id])
        user_devices = FCMDevice.objects.filter(user=self.user)
        self.assertTrue(self.mocked_send_push_notifications.called)
        self.assertEqual(
            self.mocked_send_push_notifications.call_args.args[0].count(),
            user_devices.count(),
        )
        self.assertEqual(
            self.mocked_send_push_notifications.call_args.args[0].first(),
            user_devices.first(),
        )
        message = self.mocked_send_push_notifications.call_args.kwargs["message"]
        self.assertEqual(message.notification.title, generated_message.notification.title)
        self.assertEqual(message.notification.body, generated_message.notification.body)

    @freeze_time("2022-06-8 06:00:00")
    def test_face_scan_reminder_task_with_valid_timeline_and_specified_users_no_questionnaire(
        self,
    ):
        make(FCMDevice, user=self.user)
        send_reminder_for_face_scans([self.user.id])
        self.assertFalse(self.mocked_send_push_notifications.called)
