import datetime

from django.urls import reverse
from freezegun import freeze_time
from model_bakery.baker import make
from rest_framework import status

from apps.routines import PurchaseStatus
from apps.routines.models import StatisticsPurchase
from apps.utils.tests_utils import BaseTestCase


class UserEndpointSubscriptionTestCase(BaseTestCase):
    @freeze_time("2022-09-22 13:00:00")
    def test_user_has_active_subscription(self):
        statistics_purchase = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            user=self.user,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            created_at=datetime.datetime(2022, 9, 20, 13, 00, 00),
        )

        statistics_purchase.status = PurchaseStatus.COMPLETED.value
        statistics_purchase.save(is_verified=True)

        response = self.get(reverse("user"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["active_subscriptions"][0]["id"],
            str(statistics_purchase.id),
        )
        self.assertEqual(
            response.json()["active_subscriptions"][0]["started_on"],
            statistics_purchase.purchase_started_on.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        self.assertEqual(
            response.json()["active_subscriptions"][0]["expires_on"],
            statistics_purchase.purchase_ends_after.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        self.assertEqual(
            response.json()["active_subscriptions"][0]["store_name"],
            statistics_purchase.store_name,
        )
        self.assertEqual(
            response.json()["active_subscriptions"][0]["store_product"],
            statistics_purchase.store_product_id,
        )
        self.assertEqual(len(response.json()["active_subscriptions"]), 1)

    @freeze_time("2022-09-22 13:00:00")
    def test_user_has_an_expired_but_still_active_subscription(self):
        statistics_purchase = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            user=self.user,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            created_at=datetime.datetime(2022, 9, 20, 13, 00, 00),
        )

        statistics_purchase.status = PurchaseStatus.EXPIRED.value
        statistics_purchase.save(is_verified=True)

        response = self.get(reverse("user"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["active_subscriptions"][0]["id"],
            str(statistics_purchase.id),
        )
        self.assertEqual(
            response.json()["active_subscriptions"][0]["started_on"],
            statistics_purchase.purchase_started_on.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        self.assertEqual(
            response.json()["active_subscriptions"][0]["expires_on"],
            statistics_purchase.purchase_ends_after.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        self.assertEqual(
            response.json()["active_subscriptions"][0]["store_name"],
            statistics_purchase.store_name,
        )
        self.assertEqual(
            response.json()["active_subscriptions"][0]["store_product"],
            statistics_purchase.store_product_id,
        )
        self.assertEqual(len(response.json()["active_subscriptions"]), 1)

    def test_user_only_has_subscriptions_with_other_than_completed_or_expired_status(
        self,
    ):
        make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            user=self.user,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            created_at=datetime.datetime(2022, 9, 20, 13, 00, 00),
        )
        statistics_purchase_2 = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            user=self.user,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            created_at=datetime.datetime(2022, 9, 20, 13, 00, 00),
        )
        statistics_purchase_3 = make(
            StatisticsPurchase,
            status=PurchaseStatus.STARTED.value,
            user=self.user,
            purchase_started_on=datetime.datetime(2022, 9, 20, 13, 00, 00),
            purchase_ends_after=datetime.datetime(2022, 10, 20, 13, 00, 00),
            created_at=datetime.datetime(2022, 9, 20, 13, 00, 00),
        )
        statistics_purchase_2.status = PurchaseStatus.CANCELED.value
        statistics_purchase_3.status = PurchaseStatus.PAUSED.value
        statistics_purchase_2.save(is_verified=True)
        statistics_purchase_3.save(is_verified=True)

        response = self.get(reverse("user"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["active_subscriptions"], None)

    def test_user_has_no_subscriptions(self):
        response = self.get(reverse("user"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["active_subscriptions"], None)
