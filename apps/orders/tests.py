from django.urls import reverse
from model_bakery.baker import make
from rest_framework import status

from apps.orders.admin import OrderAdmin
from apps.orders.models import Order
from apps.utils.tests_utils import BaseTestCase


class OrderTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.order_1 = make(Order, user=self.user)
        self.order_2 = make(Order, user=self.user)

    def test_order_list(self):
        url = reverse("orders-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_order_1 = response.json()["results"][0]
        response_order_2 = response.json()["results"][1]

        self.assertEqual(response_order_2["id"], str(self.order_1.id))
        self.assertEqual(
            response_order_2["created_at"],
            self.order_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response_order_2["shopify_order_id"], self.order_1.shopify_order_id)
        self.assertEqual(
            response_order_2["shopify_order_date"],
            self.order_1.shopify_order_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response_order_2["total_price"], self.order_1.total_price)
        self.assertEqual(response_order_2["currency"], self.order_1.currency)

        self.assertEqual(response_order_1["id"], str(self.order_2.id))
        self.assertEqual(
            response_order_1["created_at"],
            self.order_2.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response_order_1["shopify_order_id"], self.order_2.shopify_order_id)
        self.assertEqual(
            response_order_1["shopify_order_date"],
            self.order_2.shopify_order_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response_order_1["total_price"], self.order_2.total_price)
        self.assertEqual(response_order_1["currency"], self.order_2.currency)

    def test_order_detail(self):
        url = reverse("orders-detail", kwargs={"pk": self.order_1.pk})
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.json()["id"], str(self.order_1.id))
        self.assertEqual(
            response.json()["created_at"],
            self.order_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["shopify_order_id"], self.order_1.shopify_order_id)
        self.assertEqual(
            response.json()["shopify_order_date"],
            self.order_1.shopify_order_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["total_price"], self.order_1.total_price)
        self.assertEqual(response.json()["currency"], self.order_1.currency)

    def test_create_order(self):
        url = reverse("orders-list")
        data = {
            "shopify_order_id": "some_shopify_id_xxxx_123456789",
            "shopify_order_date": "2020-01-01 10:00:00",
            "total_price": 6000,
            "currency": "EUR",
        }
        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = Order.objects.get(user=self.user, created_at=response.json()["created_at"])
        self.assertEqual(response.json()["id"], str(order.id))
        self.assertEqual(
            response.json()["created_at"],
            order.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["shopify_order_id"], order.shopify_order_id)
        self.assertEqual(
            response.json()["shopify_order_date"],
            order.shopify_order_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        self.assertEqual(response.json()["total_price"], order.total_price)
        self.assertEqual(response.json()["currency"], order.currency)

    def test_update_order_fails(self):
        url = reverse("orders-detail", kwargs={"pk": self.order_1.pk})
        data = {
            "shopify_order_id": "some_shopify_id_xxxx_123456789",
            "shopify_order_date": "2020-01-01 10:00:00",
            "total_price": 6000,
            "currency": "EUR",
        }
        response = self.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_for_order_fails(self):
        self.query_limits["ANY PATCH REQUEST"] = 1
        url = reverse("orders-detail", kwargs={"pk": self.order_1.pk})
        data = {
            "shopify_order_id": "some_shopify_id_xxxx_123456789",
            "shopify_order_date": "2020-01-01 10:00:00",
            "total_price": 6000,
            "currency": "EUR",
        }
        response = self.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_order_data_export(self):
        exported_order = OrderAdmin.get_export_queryset(self, request=None).first()
        self.assertEqual(exported_order.user, self.order_2.user)
        self.assertEqual(exported_order.shopify_order_id, self.order_2.shopify_order_id)
        self.assertEqual(exported_order.shopify_order_date, self.order_2.shopify_order_date)
        self.assertEqual(exported_order.total_price, self.order_2.total_price)
        self.assertEqual(exported_order.currency, self.order_2.currency)
