import base64
import datetime
import json
from unittest.mock import patch
import uuid

from django.urls import reverse
from django.utils import timezone
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message
from freezegun import freeze_time
import jwt
from model_bakery.baker import make
from parameterized import parameterized
from rest_framework import status

from apps.home.models import (
    NotificationTemplate,
    NotificationTemplateTranslation,
    SiteConfiguration,
)
from apps.monetization.models import StoreProduct
from apps.questionnaire.models import UserQuestionnaire
from apps.routines import (
    AppStores,
    PurchaseStatus,
    PlayStoreSubscriptionNotificationTypes,
    AppStoreSubscriptionNotificationTypes,
    AppStoreSubscriptionNotificationGroups,
)
from apps.routines.models import StatisticsPurchase, PurchaseHistory
from apps.routines.tasks import (
    end_of_month,
    generate_reminder_message,
    send_notification_about_monthly_statistics,
)
from apps.users.models import User
from apps.utils.error_codes import Errors
from apps.utils.tests_utils import BaseTestCase


class BaseStatisticsPurchaseTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.monthly_product = make(StoreProduct)

        self.statistics_notification_template = make(
            NotificationTemplate, name="Monthly Statistics Notification Template"
        )
        self.statistics_notification_template_translation = make(
            NotificationTemplateTranslation,
            template=self.statistics_notification_template,
            language=self.user.language,
            title="Monthly Statistics Notification",
            body="Your monthly statistics is ready! Check out your achievements",
        )

        self.site_config = SiteConfiguration.get_solo()
        self.site_config.monthly_statistics_notification_template = self.statistics_notification_template
        self.site_config.save()


class StatisticsPurchaseTest(BaseStatisticsPurchaseTest):
    def test_get_statistics_purchase_list(self):
        statistics_purchase_1 = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            user=self.user,
        )
        statistics_purchase_2 = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            user=self.user,
        )
        statistics_purchase_1.status = PurchaseStatus.COMPLETED.value
        statistics_purchase_2.status = PurchaseStatus.COMPLETED.value
        statistics_purchase_1.save(is_verified=True)
        statistics_purchase_2.save(is_verified=True)

        url = reverse("statistics-purchases-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 2)
        self.assertEqual(response.json()["results"][0]["id"], str(statistics_purchase_2.id))
        self.assertEqual(response.json()["results"][1]["id"], str(statistics_purchase_1.id))

    def test_create_statistics_purchase(self):
        store_name = AppStores.PLAY_STORE.value
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=store_name,
        )
        purchase_from_db = StatisticsPurchase.objects.filter(id=statistics_purchase.id).first()
        self.assertEqual(statistics_purchase.user, purchase_from_db.user)
        self.assertEqual(statistics_purchase.store_product, purchase_from_db.store_product)
        self.assertEqual(statistics_purchase.store_name, purchase_from_db.store_name)
        self.assertEqual(statistics_purchase.receipt_data, purchase_from_db.receipt_data)
        self.assertEqual(statistics_purchase.status, purchase_from_db.status)
        self.assertEqual(
            statistics_purchase.purchase_started_on,
            purchase_from_db.purchase_started_on,
        )
        self.assertEqual(
            statistics_purchase.purchase_ends_after,
            purchase_from_db.purchase_ends_after,
        )
        self.assertEqual(statistics_purchase.transaction_id, purchase_from_db.transaction_id)
        self.assertEqual(statistics_purchase.total_transactions, 0)

    def test_start_statistics_purchase(self):
        self.query_limits["POST"] = 6
        url = reverse("statistics-purchases-start-purchase")
        data = {
            "store_name": AppStores.PLAY_STORE.value,
            "store_product": self.monthly_product.id,
        }
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        purchase = response.json()
        statistics_purchase = StatisticsPurchase.objects.first()
        self.assertEqual(str(statistics_purchase.id), purchase["id"])
        self.assertEqual(statistics_purchase.user, self.user)
        self.assertEqual(statistics_purchase.store_product_id, purchase["store_product"])
        self.assertEqual(statistics_purchase.store_name, purchase["store_name"])
        self.assertEqual(statistics_purchase.status, purchase["status"])
        self.assertEqual(statistics_purchase.receipt_data, "")
        self.assertEqual(statistics_purchase.transaction_id, "")
        self.assertIsNone(statistics_purchase.purchase_started_on)
        self.assertIsNone(statistics_purchase.purchase_ends_after)
        self.assertEqual(statistics_purchase.total_transactions, 0)
        purchase_history = PurchaseHistory.objects.filter(purchase=statistics_purchase)
        self.assertEqual(len(purchase_history), 1)
        self.assertEqual(purchase_history[0].status, statistics_purchase.status)

    def test_start_statistics_purchase_for_already_started_purchase(self):
        started_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.PLAY_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        url = reverse("statistics-purchases-start-purchase")
        data = {
            "store_name": AppStores.PLAY_STORE.value,
            "store_product": self.monthly_product.id,
        }
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], str(started_purchase.id))
        self.assertEqual(response.json()["store_product"], started_purchase.store_product_id)
        self.assertEqual(response.json()["store_name"], started_purchase.store_name)
        self.assertEqual(response.json()["purchase_started_on"], started_purchase.purchase_started_on)
        self.assertEqual(response.json()["purchase_ends_after"], started_purchase.purchase_ends_after)
        self.assertEqual(response.json()["status"], started_purchase.status)

    def test_cancel_statistics_purchase(self):
        self.query_limits["POST"] = 6
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.PLAY_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        statistics_purchase_from_db = StatisticsPurchase.objects.first()

        self.assertEqual(statistics_purchase.id, statistics_purchase_from_db.id)
        self.assertEqual(statistics_purchase.user, statistics_purchase_from_db.user)
        self.assertEqual(
            statistics_purchase.store_product_id,
            statistics_purchase_from_db.store_product_id,
        )
        self.assertEqual(statistics_purchase.store_name, statistics_purchase_from_db.store_name)
        self.assertEqual(statistics_purchase.status, statistics_purchase_from_db.status)
        self.assertEqual(statistics_purchase_from_db.status, PurchaseStatus.STARTED.value)
        self.assertEqual(statistics_purchase.receipt_data, statistics_purchase_from_db.receipt_data)
        self.assertEqual(
            statistics_purchase.transaction_id,
            statistics_purchase_from_db.transaction_id,
        )
        self.assertIsNone(
            statistics_purchase.purchase_started_on,
            statistics_purchase_from_db.purchase_started_on,
        )
        self.assertIsNone(
            statistics_purchase.purchase_ends_after,
            statistics_purchase_from_db.purchase_ends_after,
        )
        self.assertEqual(
            statistics_purchase.total_transactions,
            statistics_purchase_from_db.total_transactions,
        )

        url = reverse("statistics-purchases-cancel-purchase", args=[statistics_purchase.id])
        response = self.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        statistics_purchase_from_db.refresh_from_db()
        self.assertEqual(statistics_purchase.id, statistics_purchase_from_db.id)
        self.assertEqual(statistics_purchase.user, statistics_purchase_from_db.user)
        self.assertEqual(
            statistics_purchase.store_product_id,
            statistics_purchase_from_db.store_product_id,
        )
        self.assertEqual(statistics_purchase.store_name, statistics_purchase_from_db.store_name)
        self.assertNotEqual(statistics_purchase.status, statistics_purchase_from_db.status)
        self.assertEqual(statistics_purchase_from_db.status, PurchaseStatus.CANCELED.value)
        self.assertEqual(statistics_purchase.receipt_data, statistics_purchase_from_db.receipt_data)
        self.assertEqual(statistics_purchase.receipt_data, statistics_purchase_from_db.receipt_data)
        self.assertEqual(
            statistics_purchase.purchase_started_on,
            statistics_purchase_from_db.purchase_started_on,
        )
        self.assertEqual(
            statistics_purchase.purchase_ends_after,
            statistics_purchase_from_db.purchase_ends_after,
        )
        self.assertEqual(
            statistics_purchase.total_transactions,
            statistics_purchase_from_db.total_transactions,
        )
        purchase_history = PurchaseHistory.objects.filter(purchase=statistics_purchase_from_db)
        self.assertEqual(len(purchase_history), 1)
        self.assertEqual(purchase_history[0].status, statistics_purchase_from_db.status)

    def test_cancel_invalid_statistics_purchase(self):
        self.query_limits["POST"] = 6
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.PLAY_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        url = reverse("statistics-purchases-cancel-purchase", args=[statistics_purchase.id])
        response = self.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response1 = self.post(url)
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response1.json(), [Errors.INVALID_STATISTICS_PURCHASE_TO_CANCEL.value])

    def test_cancel_invalid_statistics_purchase_with_non_existing_purchase(self):
        url = reverse("statistics-purchases-cancel-purchase", args=[2])
        response = self.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_complete_statistics_purchase_with_empty_receipt_data(self):
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.PLAY_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        data = {}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"receipt_data": ["This field is required."]})


class MonthlyStatisticsNotificationTest(BaseStatisticsPurchaseTest):
    @freeze_time("2022-09-30 13:00:00")
    def test_end_of_month_true(self):
        current_time = timezone.now()
        self.assertTrue(end_of_month(current_time))

    @freeze_time("2022-09-15 13:00:00")
    def test_end_of_month_false(self):
        current_time = timezone.now()
        self.assertFalse(end_of_month(current_time))

    def test_generate_monthly_statistics_notification_message(self):
        notification_body = "Your monthly statistics is ready! Check out your achievements"
        generated_message = generate_reminder_message(self.statistics_notification_template_translation)
        self.assertIsInstance(generated_message, Message)
        self.assertEqual(
            generated_message.notification.title,
            self.statistics_notification_template_translation.title,
        )
        self.assertEqual(generated_message.notification.body, notification_body)

    @patch("apps.routines.tasks.send_push_notifications")
    @freeze_time("2022-09-30 13:00:00")
    def test_monthly_statistics_notification_at_the_end_of_month(self, mocked_send_push_notifications):
        make(UserQuestionnaire, user=self.user)
        statistics_purchase = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            user=self.user,
        )
        statistics_purchase.status = PurchaseStatus.COMPLETED.value
        statistics_purchase.save(is_verified=True)
        make(FCMDevice, user=self.user)

        send_notification_about_monthly_statistics()

        user_devices = FCMDevice.objects.filter(user=self.user)
        self.assertTrue(mocked_send_push_notifications.called)
        self.assertTrue(mocked_send_push_notifications.call_count, 1)
        self.assertEqual(
            mocked_send_push_notifications.call_args.args[0].first(),
            user_devices.first(),
        )

        generated_message = generate_reminder_message(self.statistics_notification_template_translation)
        message = mocked_send_push_notifications.call_args.kwargs["message"]
        self.assertEqual(message.notification.title, generated_message.notification.title)
        self.assertEqual(message.notification.body, generated_message.notification.body)

    @patch("apps.routines.tasks.send_push_notifications")
    @freeze_time("2022-09-30 13:00:00")
    def test_monthly_statistics_notification_at_the_end_of_month_no_questionnaire(self, mocked_send_push_notifications):
        statistics_purchase = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            user=self.user,
        )
        statistics_purchase.status = PurchaseStatus.COMPLETED.value
        statistics_purchase.save(is_verified=True)
        make(FCMDevice, user=self.user)

        send_notification_about_monthly_statistics()

        self.assertFalse(mocked_send_push_notifications.called)

    @patch("apps.routines.tasks.send_push_notifications")
    @freeze_time("2022-09-30 13:00:00")
    def test_monthly_statistics_notification_at_the_end_of_month_with_eligible_users(
        self, mocked_send_push_notifications
    ):
        make(UserQuestionnaire, user=self.user)
        new_user = make(User, is_verified=True, language=self.language)
        statistics_purchase_1 = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            user=self.user,
        )
        statistics_purchase_2 = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            user=new_user,
        )
        statistics_purchase_1.status = PurchaseStatus.COMPLETED.value
        statistics_purchase_1.save(is_verified=True)
        statistics_purchase_2.status = PurchaseStatus.COMPLETED.value
        statistics_purchase_2.save(is_verified=True)

        make(FCMDevice, user=self.user)
        make(FCMDevice, user=new_user)

        send_notification_about_monthly_statistics(eligible_user_pks=[self.user.id, new_user.id])

        self.assertTrue(mocked_send_push_notifications.called)
        self.assertTrue(mocked_send_push_notifications.call_count, 2)

    @patch("apps.routines.tasks.send_push_notifications")
    @freeze_time("2022-09-30 13:00:00")
    def test_monthly_statistics_notification_at_the_end_of_month_with_eligible_users_no_questionnaire(
        self, mocked_send_push_notifications
    ):
        new_user = make(User, is_verified=True, language=self.language)
        statistics_purchase_1 = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            user=self.user,
        )
        statistics_purchase_2 = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            user=new_user,
        )
        statistics_purchase_1.status = PurchaseStatus.COMPLETED.value
        statistics_purchase_1.save(is_verified=True)
        statistics_purchase_2.status = PurchaseStatus.COMPLETED.value
        statistics_purchase_2.save(is_verified=True)

        make(FCMDevice, user=self.user)
        make(FCMDevice, user=new_user)

        send_notification_about_monthly_statistics(eligible_user_pks=[self.user.id, new_user.id])

        self.assertFalse(mocked_send_push_notifications.called)

    @patch("apps.routines.tasks.send_push_notifications")
    @freeze_time("2022-09-01 6:00:00")
    def test_monthly_statistics_notification_not_at_the_end_of_month(self, mocked_send_push_notifications):
        send_notification_about_monthly_statistics()
        self.assertFalse(mocked_send_push_notifications.called)


class PlayStoreStatisticsPurchaseTest(BaseStatisticsPurchaseTest):
    @patch("apps.routines.models.get_play_store_response")
    def test_complete_statistics_purchase(self, mocked_playstore_response):
        self.query_limits["POST"] = 6
        start_time_millis = datetime.datetime.now().timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        order_id = "GPA.3312-9933-0892-83899"
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.PLAY_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        mocked_playstore_response.return_value = {
            "paymentState": 1,
            "startTimeMillis": start_time_millis,
            "expiryTimeMillis": expire_time_millis,
            "orderId": order_id,
            "obfuscatedExternalAccountId": str(statistics_purchase.id),
        }
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        purchase = StatisticsPurchase.objects.first()
        self.assertEqual(purchase.user, self.user)
        self.assertEqual(purchase.status, PurchaseStatus.COMPLETED.value)
        self.assertEqual(purchase.store_name, AppStores.PLAY_STORE.value)
        self.assertEqual(purchase.receipt_data, data["receipt_data"])
        self.assertEqual(purchase.transaction_id, order_id)
        self.assertEqual(purchase.total_transactions, 1)
        self.assertEqual(
            purchase.purchase_started_on.date(),
            datetime.datetime.fromtimestamp(start_time_millis / 1000).date(),
        )
        self.assertEqual(
            purchase.purchase_ends_after.date(),
            datetime.datetime.fromtimestamp(expire_time_millis / 1000).date(),
        )
        purchase_history = PurchaseHistory.objects.filter(purchase=purchase)
        self.assertEqual(len(purchase_history), 1)
        self.assertEqual(purchase_history[0].status, purchase.status)

    @patch("apps.routines.models.get_play_store_response")
    def test_complete_statistics_purchase_with_invalid_payment(self, mocked_playstore_response):
        start_time_millis = datetime.datetime.now().timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        order_id = "GPA.3312-9933-0892-83899"
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.PLAY_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        mocked_playstore_response.return_value = {
            "paymentState": 0,
            "startTimeMillis": start_time_millis,
            "expiryTimeMillis": expire_time_millis,
            "orderId": order_id,
            "obfuscatedExternalAccountId": str(statistics_purchase.id),
        }
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), [Errors.PURCHASE_PAYMENT_IS_NOT_YET_RECEIVED.value])

    @patch("apps.routines.models.get_play_store_response")
    def test_complete_statistics_purchase_with_cancelled_subscription(self, mocked_playstore_response):
        start_time_millis = datetime.datetime.now().timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        order_id = "GPA.3312-9933-0892-83899"
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.PLAY_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        mocked_playstore_response.return_value = {
            "cancelReason": 0,
            "startTimeMillis": start_time_millis,
            "expiryTimeMillis": expire_time_millis,
            "orderId": order_id,
            "obfuscatedExternalAccountId": str(statistics_purchase.id),
        }
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), [Errors.SUBSCRIPTION_PURCHASE_WAS_CANCELLED.value])

    @patch("apps.routines.models.get_play_store_response")
    def test_complete_statistics_purchase_with_no_obfuscated_account_id_in_token(self, mocked_playstore_response):
        start_time_millis = datetime.datetime.now().timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        order_id = "GPA.3312-9933-0892-83899"
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.PLAY_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        mocked_playstore_response.return_value = {
            "paymentState": 1,
            "startTimeMillis": start_time_millis,
            "expiryTimeMillis": expire_time_millis,
            "orderId": order_id,
        }
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), [Errors.NO_OBFUSCATED_ACCOUNT_ID_FOUND.value])

    @patch("apps.routines.models.get_play_store_response")
    def test_complete_statistics_purchase_with_shared_token(self, mocked_playstore_response):
        different_obfuscated_uuid = uuid.uuid4()
        start_time_millis = datetime.datetime.now().timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        order_id = "GPA.3312-9933-0892-83899"
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.PLAY_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        mocked_playstore_response.return_value = {
            "paymentState": 1,
            "startTimeMillis": start_time_millis,
            "expiryTimeMillis": expire_time_millis,
            "orderId": order_id,
            "obfuscatedExternalAccountId": str(different_obfuscated_uuid),
        }
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), [Errors.PURCHASE_TOKEN_BELONGS_TO_OTHER_USER.value])

    @patch("apps.routines.models.get_app_store_response")
    def test_complete_statistics_purchase_with_shared_token_existing_expired_purchase(self, mocked_appstore_response):
        self.query_limits["POST"] = 7
        initial_obfuscated_uuid = uuid.uuid4()
        purchase_time_millis = datetime.datetime.now().timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        original_transaction_id = "1000000831360853"
        make(
            StatisticsPurchase,
            id=initial_obfuscated_uuid,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.APP_STORE.value,
            status=PurchaseStatus.EXPIRED.value,
        )
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.APP_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        mocked_appstore_response.return_value.json.return_value = {
            "latest_receipt_info": [
                {
                    "purchase_date_ms": purchase_time_millis,
                    "expires_date_ms": expire_time_millis,
                    "original_transaction_id": original_transaction_id,
                    "app_account_token": str(initial_obfuscated_uuid),
                }
            ]
        }
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch("apps.routines.models.get_play_store_response")
    def test_complete_statistics_purchase_with_auto_resume(self, mocked_playstore_response):
        self.query_limits["POST"] = 6
        start_time_millis = datetime.datetime.now().timestamp()
        auto_resume_time_millis = (datetime.datetime.now() + datetime.timedelta(days=2)).timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        order_id = "GPA.3312-9933-0892-83899"
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.PLAY_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        mocked_playstore_response.return_value = {
            "paymentState": 1,
            "startTimeMillis": start_time_millis,
            "expiryTimeMillis": expire_time_millis,
            "autoResumeTimeMillis": auto_resume_time_millis,
            "orderId": order_id,
            "obfuscatedExternalAccountId": str(statistics_purchase.id),
        }
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        purchase = StatisticsPurchase.objects.first()
        self.assertEqual(purchase.user, self.user)
        self.assertEqual(purchase.status, PurchaseStatus.COMPLETED.value)
        self.assertEqual(purchase.store_name, AppStores.PLAY_STORE.value)
        self.assertEqual(purchase.receipt_data, data["receipt_data"])
        self.assertEqual(purchase.transaction_id, order_id)
        self.assertEqual(purchase.total_transactions, 1)
        self.assertEqual(
            purchase.purchase_started_on.date(),
            datetime.datetime.fromtimestamp(auto_resume_time_millis / 1000).date(),
        )
        self.assertEqual(
            purchase.purchase_ends_after.date(),
            datetime.datetime.fromtimestamp(expire_time_millis / 1000).date(),
        )

    @parameterized.expand(
        [
            [
                PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_RECOVERED,
                PurchaseStatus.COMPLETED,
            ],
            [
                PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_RENEWED,
                PurchaseStatus.COMPLETED,
            ],
            [
                PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_CANCELED,
                PurchaseStatus.EXPIRED,
            ],
            [
                PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_PURCHASED,
                PurchaseStatus.COMPLETED,
            ],
            [
                PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_ON_HOLD,
                PurchaseStatus.EXPIRED,
            ],
            [
                PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_IN_GRACE_PERIOD,
                PurchaseStatus.COMPLETED,
            ],
            [
                PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_RESTARTED,
                PurchaseStatus.COMPLETED,
            ],
            [
                PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_PRICE_CHANGE_CONFIRMED,
                PurchaseStatus.COMPLETED,
            ],
            [
                PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_DEFERRED,
                PurchaseStatus.COMPLETED,
            ],
            [
                PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_PAUSED,
                PurchaseStatus.PAUSED,
            ],
            [
                PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_PAUSE_SCHEDULE_CHANGED,
                PurchaseStatus.PAUSED,
            ],
            [
                PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_REVOKED,
                PurchaseStatus.EXPIRED,
            ],
            [
                PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_EXPIRED,
                PurchaseStatus.EXPIRED,
            ],
        ]
    )
    @patch("apps.routines.purchases.get_play_store_response")
    def test_statistics_subscription_purchase_notification_with_webhook(
        self, notification_type, subscription_purchase_status, mocked_playstore_response
    ):
        start_time_millis = datetime.datetime.now().timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        order_id = "GPA.3312-9933-0892-83899..0"
        purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.PLAY_STORE.value,
            receipt_data=self._get_purchase_token(),
            status=PurchaseStatus.STARTED.value,
            total_transactions=1,
            transaction_id=order_id.split("..")[0],
        )
        purchase.status = PurchaseStatus.COMPLETED.value
        purchase.save(is_verified=True)
        mocked_playstore_response.return_value = {
            "paymentState": 1,
            "startTimeMillis": start_time_millis,
            "expiryTimeMillis": expire_time_millis,
            "orderId": order_id,
            "obfuscatedExternalAccountId": str(purchase.id),
        }
        statistics_purchase = StatisticsPurchase.objects.filter(user=self.user).first()
        self.assertIsNone(statistics_purchase.purchase_started_on)
        self.assertIsNone(statistics_purchase.purchase_ends_after)
        self.assertEqual(statistics_purchase.status, PurchaseStatus.COMPLETED.value)

        data = self._get_notification_message(notification_type)
        url = reverse("statistics-purchases-play-store-webhook")
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statistics_purchase.refresh_from_db()
        self.assertEqual(
            statistics_purchase.purchase_started_on.date(),
            datetime.datetime.fromtimestamp(start_time_millis / 1000).date(),
        )
        self.assertEqual(
            statistics_purchase.purchase_ends_after.date(),
            datetime.datetime.fromtimestamp(expire_time_millis / 1000).date(),
        )
        self.assertEqual(statistics_purchase.status, subscription_purchase_status)
        if subscription_purchase_status == PurchaseStatus.COMPLETED.value:
            self.assertEqual(statistics_purchase.total_transactions, 2)
        else:
            self.assertEqual(statistics_purchase.total_transactions, 1)
        self.assertEqual(statistics_purchase.transaction_id, order_id.split("..")[0])
        self.assertEqual(statistics_purchase.receipt_data, self._get_purchase_token())
        purchase_history = PurchaseHistory.objects.filter(purchase=statistics_purchase)
        self.assertEqual(len(purchase_history), 1)
        self.assertEqual(purchase_history[0].status, statistics_purchase.status)

    @patch("apps.routines.views.process_statistics_purchase_play_store_notifications")
    def test_statistics_subscription_purchase_notification_webhook_with_empty_message_data(
        self, mocked_process_statistics_purchase_notifications
    ):
        url = reverse("statistics-purchases-play-store-webhook")
        response = self.post(url, data={})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(mocked_process_statistics_purchase_notifications.called)

    @patch("apps.routines.views.process_statistics_purchase_play_store_notifications")
    def test_statistics_subscription_purchase_notification_webhook_with_invalid_message_data(
        self, mocked_process_statistics_purchase_notifications
    ):
        data = self._get_notification_message()
        encoded_data = data["message"]["data"][:-4]
        data["message"]["data"] = encoded_data
        url = reverse("statistics-purchases-play-store-webhook")
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(mocked_process_statistics_purchase_notifications.called)

    @patch("apps.routines.purchases.LOGGER.warning")
    def test_statistics_subscription_purchase_notification_webhook_with_non_associated_receipt_data(
        self, mocked_warning_log
    ):
        data = self._get_notification_message()
        url = reverse("statistics-purchases-play-store-webhook")
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(mocked_warning_log.called)

    @patch("apps.routines.purchases.get_play_store_response")
    def test_statistics_subscription_purchase_notification_webhook_with_shared_receipt_data(
        self, mocked_play_store_response
    ):
        shared_obfuscated_account_id = uuid.uuid4()
        start_time_millis = datetime.datetime.now().timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        order_id = "GPA.3312-9933-0892-83899..0"
        purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.PLAY_STORE.value,
            receipt_data=self._get_purchase_token(),
            status=PurchaseStatus.STARTED.value,
            total_transactions=1,
            transaction_id=order_id.split("..")[0],
        )
        purchase.status = PurchaseStatus.COMPLETED.value
        purchase.save(is_verified=True)
        mocked_play_store_response.return_value = {
            "paymentState": 1,
            "startTimeMillis": start_time_millis,
            "expiryTimeMillis": expire_time_millis,
            "orderId": order_id,
            "obfuscatedExternalAccountId": str(shared_obfuscated_account_id),
        }
        data = self._get_notification_message()
        url = reverse("statistics-purchases-play-store-webhook")
        with patch("apps.routines.purchases.LOGGER.warning") as mocked_warning_log:
            response = self.post(url, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(mocked_warning_log.called)

    @parameterized.expand(
        [
            [
                "GPA.3312-9933-0892-83899",
                1,
                {
                    "message": "Could not parse orderId [%s] for statistics purchase [%s].",
                    "type": "error",
                    "index": 0,
                    "arguments": ["order_id", "purchase_id"],
                },
            ],
            [
                "GPA.3312-9933-0892-83899..0",
                2,
                {
                    "message": "Statistics subscription purchase [%s] validity remains until [%s].",
                    "type": "info",
                    "index": 4,
                    "arguments": ["purchase_id", "expire_time"],
                },
            ],
        ]
    )
    @patch("apps.routines.purchases.LOGGER.error")
    @patch("apps.routines.purchases.LOGGER.info")
    @patch("apps.routines.purchases.LOGGER.debug")
    @patch("apps.routines.purchases.LOGGER.warning")
    @patch("apps.routines.purchases.get_play_store_response")
    def test_subscription_purchase_notification_webhook_with_shared_receipt_data_order_id(  # noqa: CFQ002
        self,
        order_id,
        total_transactions,
        metadata,
        mocked_play_store_response,
        warning_mock,
        debug_mock,
        info_mock,
        error_mock,
    ):
        import pytz

        mocks = {
            "debug": debug_mock,
            "info": info_mock,
            "warning": warning_mock,
            "error": error_mock,
        }
        expire_time = timezone.now() + datetime.timedelta(days=10)
        start_time_millis = datetime.datetime.now().timestamp()
        expire_time_millis = expire_time.timestamp()
        purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.PLAY_STORE.value,
            receipt_data=self._get_purchase_token(),
            status=PurchaseStatus.STARTED.value,
            total_transactions=1,
            transaction_id=order_id,
        )
        purchase.status = PurchaseStatus.COMPLETED.value
        purchase.save(is_verified=True)
        mocked_play_store_response.return_value = {
            "paymentState": 1,
            "startTimeMillis": start_time_millis,
            "expiryTimeMillis": expire_time_millis * 1000,
            "orderId": order_id,
            "obfuscatedExternalAccountId": str(purchase.id),
        }
        data = self._get_notification_message()
        url = reverse("statistics-purchases-play-store-webhook")

        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        purchase.refresh_from_db()
        self.assertEqual(purchase.total_transactions, total_transactions)

        message_data = {
            "purchase_id": purchase.id,
            "order_id": order_id,
            "expire_time": datetime.datetime.fromtimestamp(int(expire_time_millis * 1000) / 1000, tz=pytz.UTC),
        }

        expected = {
            "warning": [],
            "debug": [
                (("Successfully decoded base64 encoded data.",), {}),
                (
                    (
                        "Statistics subscription purchase [%s] has been updated successfully.",
                        purchase.id,
                    ),
                    {},
                ),
            ],
            "info": [
                (
                    ("Received statistics subscription purchase notification from google play store.",),
                    {},
                ),
                (("Starting decoding base64 encoded data.",), {}),
                (
                    (
                        "Processing statistics subscription purchase notification message [%s].",
                        data["message"]["message_id"],
                    ),
                    {},
                ),
                (
                    ("Started to process play store statistics purchase notifications.",),
                    {},
                ),
            ],
            "error": [],
        }

        expected[metadata["type"]].insert(
            metadata["index"],
            (
                (
                    metadata["message"],
                    *[message_data[argument] for argument in metadata["arguments"]],
                ),
                {},
            ),
        )

        for log_level, expected_calls in expected.items():
            self.assertEqual(mocks[log_level].call_args_list, expected_calls, log_level)

    def _get_notification_message(self, notification_type=None):
        message_data = {
            "message": {
                "data": self._get_encoded_notification(notification_type),
                "messageId": "2829603729517390",
                "message_id": "2829603729517390",
                "publishTime": "2022-07-02T20:49:59.124Z",
                "publish_time": "2022-07-02T20:49:59.124Z",
            },
            "subscription": "projects/935083/subscriptions/systemakvile-rtdn",
        }
        return message_data

    def _get_encoded_notification(self, notification_type=None):
        if not notification_type:
            notification_type = 4
        data = {
            "version": "1.0",
            "packageName": "com.systemakvile",
            "eventTimeMillis": "1630529397125",
            "subscriptionNotification": {
                "version": "1.0",
                "notificationType": notification_type,
                "purchaseToken": self._get_purchase_token(),
                "subscriptionId": "sa_099_1m",
            },
        }
        return base64.b64encode(json.dumps(data).encode("utf-8"))

    def _get_purchase_token(self):
        token = (
            "ibdeahmpfcpbbnigegcigahf.AO-J1OxZvdmd4wJAUaW2F7nlyNrbdt1UZZQpHSOcUSly"  # noqa: S105
            "TRmDvPkQYNLkDNSVhErk_tphqziANW6WMypKQaeXwqL5pP-_6Mu4xA"
        )
        return token


class AppStoreStatisticsPurchaseTest(BaseStatisticsPurchaseTest):
    @patch("apps.routines.models.get_app_store_response")
    def test_complete_statistics_purchase(self, mocked_appstore_response):
        self.query_limits["POST"] = 6
        purchase_time_millis = datetime.datetime.now().timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        original_transaction_id = "1000000831360853"
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.APP_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        mocked_appstore_response.return_value.json.return_value = {
            "latest_receipt_info": [
                {
                    "purchase_date_ms": purchase_time_millis,
                    "expires_date_ms": expire_time_millis,
                    "original_transaction_id": original_transaction_id,
                    "app_account_token": str(statistics_purchase.id),
                }
            ]
        }
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        purchase = StatisticsPurchase.objects.first()
        self.assertEqual(purchase.user, self.user)
        self.assertEqual(purchase.status, PurchaseStatus.COMPLETED.value)
        self.assertEqual(purchase.store_name, AppStores.APP_STORE.value)
        self.assertEqual(purchase.receipt_data, data["receipt_data"])
        self.assertEqual(purchase.transaction_id, original_transaction_id)
        self.assertEqual(purchase.total_transactions, 1)
        self.assertEqual(
            purchase.purchase_started_on.date(),
            datetime.datetime.fromtimestamp(purchase_time_millis / 1000).date(),
        )
        self.assertEqual(
            purchase.purchase_ends_after.date(),
            datetime.datetime.fromtimestamp(expire_time_millis / 1000).date(),
        )
        purchase_history = PurchaseHistory.objects.filter(purchase=purchase)
        self.assertEqual(len(purchase_history), 1)
        self.assertEqual(purchase_history[0].status, purchase.status)

    @patch("apps.routines.models.get_app_store_response")
    def test_complete_statistics_purchase_with_invalid_status(self, mocked_appstore_response):
        mocked_appstore_response.return_value.json.return_value = {"status": 21002}
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.APP_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), [Errors.UNEXPECTED_ERROR_FROM_APP_STORE.value])

    @patch("apps.routines.models.get_app_store_response")
    def test_complete_statistics_purchase_with_no_app_account_token(self, mocked_appstore_response):
        purchase_time_millis = datetime.datetime.now().timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        original_transaction_id = "1000000831360853"

        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.APP_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        mocked_appstore_response.return_value.json.return_value = {
            "latest_receipt_info": [
                {
                    "purchase_date_ms": purchase_time_millis,
                    "expires_date_ms": expire_time_millis,
                    "original_transaction_id": original_transaction_id,
                }
            ]
        }
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), [Errors.NO_APP_ACCOUNT_TOKEN_FOUND.value])

    @patch("apps.routines.models.get_app_store_response")
    def test_complete_statistics_purchase_shared_token(self, mocked_appstore_response):
        different_account_id = uuid.uuid4()
        purchase_time_millis = datetime.datetime.now().timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        original_transaction_id = "1000000831360853"

        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.APP_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        mocked_appstore_response.return_value.json.return_value = {
            "latest_receipt_info": [
                {
                    "purchase_date_ms": purchase_time_millis,
                    "expires_date_ms": expire_time_millis,
                    "original_transaction_id": original_transaction_id,
                    "app_account_token": str(different_account_id),
                }
            ]
        }
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), [Errors.PURCHASE_TOKEN_BELONGS_TO_OTHER_USER.value])

    @patch("apps.routines.models.get_app_store_response")
    def test_complete_statistics_purchase_shared_token_existing_expired_purchase(self, mocked_appstore_response):
        self.query_limits["POST"] = 7
        initial_app_account_token = uuid.uuid4()
        purchase_time_millis = datetime.datetime.now().timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        original_transaction_id = "1000000831360853"
        make(
            StatisticsPurchase,
            id=initial_app_account_token,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.APP_STORE.value,
            status=PurchaseStatus.EXPIRED.value,
        )
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.APP_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        mocked_appstore_response.return_value.json.return_value = {
            "latest_receipt_info": [
                {
                    "purchase_date_ms": purchase_time_millis,
                    "expires_date_ms": expire_time_millis,
                    "original_transaction_id": original_transaction_id,
                    "app_account_token": str(initial_app_account_token),
                }
            ]
        }
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch("apps.routines.models.get_app_store_response")
    def test_complete_statistics_purchase_with_cancelled_subscription(self, mocked_appstore_response):
        mocked_appstore_response.return_value.json.return_value = {"pending_renewal_info": [{"expiration_intent": 1}]}
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.APP_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), [Errors.SUBSCRIPTION_PURCHASE_WAS_CANCELLED.value])

    @patch("apps.routines.models.get_app_store_response")
    def test_complete_statistics_purchase_with_empty_latest_info(self, mocked_appstore_response):
        mocked_appstore_response.return_value.json.return_value = {"receipt": {}}
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.APP_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), [Errors.NO_PURCHASE_IN_RECEIPT.value])

    @patch("apps.routines.models.get_app_store_response")
    def test_complete_statistics_purchase_with_grace_period(self, mocked_appstore_response):
        self.query_limits["POST"] = 6
        purchase_time_millis = datetime.datetime.now().timestamp()
        auto_resume_time_millis = (datetime.datetime.now() + datetime.timedelta(days=2)).timestamp()
        grace_period_millis = (datetime.datetime.now() + datetime.timedelta(days=8)).timestamp()
        expire_time_millis = (datetime.datetime.now() + datetime.timedelta(days=10)).timestamp()
        original_transaction_id = "1000000831360853"
        statistics_purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.APP_STORE.value,
            status=PurchaseStatus.STARTED.value,
        )
        mocked_appstore_response.return_value.json.return_value = {
            "latest_receipt_info": [
                {
                    "purchase_date_ms": purchase_time_millis,
                    "expires_date_ms": expire_time_millis,
                    "original_transaction_id": original_transaction_id,
                    "app_account_token": str(statistics_purchase.id),
                }
            ],
            "pending_renewal_info": [{"grace_period_expires_date_ms": grace_period_millis}],
        }
        data = {"receipt_data": "need-some-base64-encoded-string"}
        url = reverse("statistics-purchases-complete-purchase", args=[statistics_purchase.id])
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        purchase = StatisticsPurchase.objects.first()
        self.assertEqual(purchase.user, self.user)
        self.assertEqual(purchase.status, PurchaseStatus.COMPLETED.value)
        self.assertEqual(purchase.store_name, AppStores.APP_STORE.value)
        self.assertEqual(purchase.receipt_data, data["receipt_data"])
        self.assertEqual(purchase.transaction_id, original_transaction_id)
        self.assertEqual(purchase.total_transactions, 1)
        self.assertEqual(
            purchase.purchase_started_on.date(),
            datetime.datetime.fromtimestamp(auto_resume_time_millis / 1000).date(),
        )
        self.assertEqual(
            purchase.purchase_ends_after.date(),
            datetime.datetime.fromtimestamp(grace_period_millis / 1000).date(),
        )

    @patch("apps.routines.views.process_statistics_purchase_app_store_notification")
    def test_statistics_subscription_purchase_notification_webhook_with_empty_message_data(
        self, mocked_process_statistics_purchase_notifications
    ):
        url = reverse("statistics-purchases-apps-store-webhook")
        response = self.post(url, data={})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(mocked_process_statistics_purchase_notifications.called)

    @patch("apps.routines.purchases.LOGGER.warning")
    def test_statistics_subscription_purchase_notification_webhook_with_non_associated_receipt_data_with_did_renew(
        self, mocked_warning_log
    ):
        data = self._get_signed_payload(AppStoreSubscriptionNotificationTypes.DID_RENEW.value)
        url = reverse("statistics-purchases-apps-store-webhook")
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(mocked_warning_log.called)

    @patch("apps.routines.purchases.get_app_store_response")
    def test_statistics_subscription_purchase_notification_webhook_with_non_associated_subscription_purchase(
        self, mocked_appstore_response
    ):
        data = self._get_signed_payload(AppStoreSubscriptionNotificationTypes.SUBSCRIBED.value)
        purchase_id = uuid.uuid4()
        verified_data = self._get_verified_receipt_data(str(purchase_id))
        mocked_appstore_response.return_value.json.return_value = verified_data
        statistics_purchases = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.APP_STORE.value,
            status=PurchaseStatus.EXPIRED.value,
            receipt_data=self._get_receipt_data(),
            transaction_id=self._get_latest_receipt_info(str(purchase_id))[0]["original_transaction_id"],
            total_transactions=1,
            _quantity=3,
        )
        statistics_purchases[2].transaction_id = ""
        statistics_purchases[2].receipt_data = ""
        statistics_purchases[2].purchase_started_on = None
        statistics_purchases[2].purchase_ends_after = None
        statistics_purchases[2].status = PurchaseStatus.STARTED.value
        statistics_purchases[2].save(is_verified=True)
        url = reverse("statistics-purchases-apps-store-webhook")
        with patch("apps.routines.purchases.LOGGER.warning") as mocked_warning_log:
            response = self.post(url, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(mocked_warning_log.called)

    @parameterized.expand(
        [
            [
                AppStoreSubscriptionNotificationTypes.DID_CHANGE_RENEWAL_PREF,
                PurchaseStatus.COMPLETED,
            ],
            [
                AppStoreSubscriptionNotificationTypes.DID_CHANGE_RENEWAL_STATUS,
                PurchaseStatus.COMPLETED,
            ],
            [
                AppStoreSubscriptionNotificationTypes.DID_FAIL_TO_RENEW,
                PurchaseStatus.COMPLETED,
            ],
            [AppStoreSubscriptionNotificationTypes.DID_RENEW, PurchaseStatus.COMPLETED],
            [
                AppStoreSubscriptionNotificationTypes.OFFER_REDEEMED,
                PurchaseStatus.COMPLETED,
            ],
            [
                AppStoreSubscriptionNotificationTypes.PRICE_INCREASE,
                PurchaseStatus.COMPLETED,
            ],
            [
                AppStoreSubscriptionNotificationTypes.REFUND_DECLINED,
                PurchaseStatus.COMPLETED,
            ],
            [
                AppStoreSubscriptionNotificationTypes.RENEWAL_EXTENDED,
                PurchaseStatus.COMPLETED,
            ],
            [
                AppStoreSubscriptionNotificationTypes.SUBSCRIBED,
                PurchaseStatus.COMPLETED,
            ],
            [AppStoreSubscriptionNotificationTypes.EXPIRED, PurchaseStatus.EXPIRED],
            [
                AppStoreSubscriptionNotificationTypes.GRACE_PERIOD_EXPIRED,
                PurchaseStatus.EXPIRED,
            ],
            [AppStoreSubscriptionNotificationTypes.REFUND, PurchaseStatus.EXPIRED],
            [AppStoreSubscriptionNotificationTypes.REVOKE, PurchaseStatus.EXPIRED],
        ]
    )
    @patch("apps.routines.purchases.get_app_store_response")
    def test_statistics_subscription_purchase_notification_with_webhook(
        self, notification_type, subscription_purchase_status, mocked_appstore_response
    ):
        purchase_id = uuid.uuid4()
        verified_data = self._get_verified_receipt_data(str(purchase_id))
        transaction_id = self._get_latest_receipt_info(purchase_id)[0]["original_transaction_id"]
        start_time_millis = self._get_latest_receipt_info(purchase_id)[0]["purchase_date_ms"]
        expire_time_millis = self._get_latest_receipt_info(purchase_id)[0]["expires_date_ms"]

        if (
            notification_type == AppStoreSubscriptionNotificationTypes.DID_CHANGE_RENEWAL_STATUS.value
            and subscription_purchase_status == PurchaseStatus.EXPIRED.value
        ):
            verified_data["pending_renewal_info"][0]["expiration_intent"] = 2

        mocked_appstore_response.return_value.json.return_value = verified_data
        purchase = make(
            StatisticsPurchase,
            user=self.user,
            store_product=self.monthly_product,
            store_name=AppStores.APP_STORE.value,
            status=PurchaseStatus.STARTED.value,
            receipt_data=self._get_receipt_data(),
            transaction_id=transaction_id,
            total_transactions=1,
            id=purchase_id,
        )
        purchase.status = PurchaseStatus.COMPLETED.value
        purchase.save(is_verified=True)
        statistics_purchase = StatisticsPurchase.objects.filter(user=self.user).first()
        self.assertEqual(purchase.id, purchase_id)
        self.assertIsNone(statistics_purchase.purchase_started_on)
        self.assertIsNone(statistics_purchase.purchase_ends_after)
        self.assertEqual(statistics_purchase.status, PurchaseStatus.COMPLETED.value)
        self.assertEqual(statistics_purchase.total_transactions, 1)
        self.assertEqual(statistics_purchase.receipt_data, self._get_receipt_data())
        data = self._get_signed_payload(notification_type)
        url = reverse("statistics-purchases-apps-store-webhook")
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statistics_purchase.refresh_from_db()
        self.assertEqual(
            statistics_purchase.purchase_started_on.date(),
            datetime.datetime.fromtimestamp(int(start_time_millis) / 1000).date(),
        )
        self.assertEqual(
            statistics_purchase.purchase_ends_after.date(),
            datetime.datetime.fromtimestamp(int(expire_time_millis) / 1000).date(),
        )
        self.assertEqual(statistics_purchase.status, subscription_purchase_status)
        if notification_type in AppStoreSubscriptionNotificationGroups.RENEWAL_TYPES:
            self.assertEqual(statistics_purchase.total_transactions, 2)
        else:
            self.assertEqual(statistics_purchase.total_transactions, 1)
        self.assertEqual(statistics_purchase.transaction_id, transaction_id)
        self.assertEqual(statistics_purchase.receipt_data, self._get_receipt_data())
        purchase_history = PurchaseHistory.objects.filter(purchase=statistics_purchase)
        self.assertEqual(len(purchase_history), 1)
        self.assertEqual(purchase_history[0].status, statistics_purchase.status)

    def _get_verified_receipt_data(self, purchase_id):
        data = {
            "environment": "Sandbox",
            "receipt": {
                "receipt_type": "Sandbox",
                "adam_id": 123,
                "app_item_id": 123,
                "bundle_id": "com.systemakvile",
                "application_version": "1",
                "download_id": 123,
                "version_external_identifier": 123,
                "receipt_creation_date": "2021-04-28 19:42:01 Etc/GMT",
                "receipt_creation_date_ms": "1619638921000",
                "receipt_creation_date_pst": "2021-04-28 12:42:01 America/Los_Angeles",
                "request_date": "2021-08-09 18:26:02 Etc/GMT",
                "request_date_ms": "1628533562696",
                "request_date_pst": "2021-08-09 11:26:02 America/Los_Angeles",
                "original_purchase_date": "2017-04-09 21:18:41 Etc/GMT",
                "original_purchase_date_ms": "1491772721000",
                "original_purchase_date_pst": "2017-04-09 14:18:41 America/Los_Angeles",
                "original_application_version": "1",
            },
            "latest_receipt_info": self._get_latest_receipt_info(purchase_id),
            "latest_receipt": self._get_receipt_data(),
            "pending_renewal_info": self._get_pending_renewal_info(),
            "status": 0,
        }
        return data

    def _get_latest_receipt_info(self, purchase_id):
        return [
            {
                "quantity": "1",
                "product_id": "sa_099_1m",
                "transaction_id": "230001020690335",
                "original_transaction_id": "1000000831360853",
                "purchase_date": "2021-08-04 19:41:58 Etc/GMT",
                "purchase_date_ms": "1628106118000",
                "purchase_date_pst": "2021-08-04 12:41:58 America/Los_Angeles",
                "original_purchase_date": "2021-04-28 19:41:58 Etc/GMT",
                "original_purchase_date_ms": "1619638918000",
                "original_purchase_date_pst": "2021-04-28 12:41:58 America/Los_Angeles",
                "expires_date": "2021-08-11 19:41:58 Etc/GMT",
                "expires_date_ms": "1628710918000",
                "expires_date_pst": "2021-08-11 12:41:58 America/Los_Angeles",
                "web_order_line_item_id": "230000438372383",
                "is_trial_period": "false",
                "is_in_intro_offer_period": "false",
                "in_app_ownership_type": "PURCHASED",
                "subscription_group_identifier": "272394410",
                "app_account_token": purchase_id,
            }
        ]

    def _get_pending_renewal_info(self):
        return [
            {
                "auto_renew_product_id": "sa_099_1m",
                "product_id": "sa_099_1m",
                "original_transaction_id": "1000000831360853",
                "auto_renew_status": "1",
            }
        ]

    def _get_receipt_data(self):
        receipt_data = "ibdeahmpfcpbbnigegcigahf.AO-J1OxZvdmd4wJAUaW2F7nlyNrbdt1UZZQpHSOcUSly"  # noqa: S105
        return receipt_data

    def _get_signed_payload(self, notification_status=AppStoreSubscriptionNotificationTypes.DID_RENEW.value):
        raw_data = self._notification_data(notification_status)
        unified_receipt_data = {}
        parsed_data_attrs = [
            "notificationType",
            "subtype",
            "notificationUUID",
            "data",
            "version",
            "signedDate",
        ]
        for attr in parsed_data_attrs:
            if attr == "data":
                parsable_notification_data_attrs = [
                    "signedTransactionInfo",
                    "signedRenewalInfo",
                ]
                notification_data_attrs = [
                    "bundleId",
                    "bundleVersion",
                    "environment",
                ] + parsable_notification_data_attrs
                notification_data = {}
                for notification_data_attr in notification_data_attrs:
                    if notification_data_attr in parsable_notification_data_attrs:
                        notification_data.update(
                            {notification_data_attr: self._encode_jwt(raw_data[attr][notification_data_attr])}
                        )
                    else:
                        notification_data.update({notification_data_attr: raw_data[attr][notification_data_attr]})
                unified_receipt_data.update({attr: notification_data})
            else:
                unified_receipt_data.update({attr: raw_data.get(attr)})
        return {"signedPayload": self._encode_jwt(unified_receipt_data)}

    def _notification_data(self, notification_status=AppStoreSubscriptionNotificationTypes.DID_RENEW.value):
        data = {
            "notificationType": notification_status,
            "subtype": "VOLUNTARY",
            "notificationUUID": "cab180e2-902a-4d4c-a17c-a17c2b44d593",
            "data": {
                "bundleId": "com.systemakvile.app",
                "bundleVersion": "1",
                "environment": "Sandbox",
                "signedTransactionInfo": {
                    "transactionId": "2000000153048533",
                    "originalTransactionId": "1000000831360853",
                    "webOrderLineItemId": "2000000010884136",
                    "bundleId": "com.systemakvile.app",
                    "productId": "sa_1299_1m",
                    "subscriptionGroupIdentifier": "21010157",
                    "purchaseDate": 1663058085000,
                    "originalPurchaseDate": 1660732591000,
                    "expiresDate": 1663058385000,
                    "quantity": 1,
                    "type": "Auto-Renewable Subscription",
                    "inAppOwnershipType": "PURCHASED",
                    "signedDate": 1663058596724,
                    "environment": "Sandbox",
                },
                "signedRenewalInfo": {
                    "originalTransactionId": "1000000831360853",
                    "autoRenewProductId": "sa_1299_1m",
                    "productId": "sa_1299_1m",
                    "autoRenewStatus": 1,
                    "isInBillingRetryPeriod": False,
                    "signedDate": 1663058596703,
                    "environment": "Sandbox",
                    "recentSubscriptionStartDate": 1663055345000,
                },
            },
            "version": "2.0",
            "signedDate": 1663058596759,
        }
        if notification_status == AppStoreSubscriptionNotificationTypes.EXPIRED.value:
            data["data"]["signedRenewalInfo"].update({"expirationIntent": 1})
        return data

    def _encode_jwt(self, payload: dict) -> str:
        return jwt.encode(payload, key="just_a_secret")
