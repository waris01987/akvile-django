from model_bakery.baker import make
from rest_framework import status
from rest_framework.reverse import reverse

from apps.monetization.models import StoreProduct
from apps.utils.tests_utils import BaseTestCase


class StoreProductTestCase(BaseTestCase):
    def test_create_store_products(self):
        name = "Monthly subscription for Android"
        description = "A test subscription"
        sku = "sa_199_1y"
        store_product = make(StoreProduct, name=name, description=description, sku=sku)
        self.assertEqual(store_product.name, name)
        self.assertEqual(store_product.description, description)
        self.assertEqual(store_product.sku, sku)
        self.assertTrue(store_product.is_enabled)
        self.assertFalse(store_product.is_default)

    def test_get_store_products(self):
        url = reverse("products-list")
        store_product = make(StoreProduct)
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], store_product.pk)
        self.assertEqual(results[0]["name"], store_product.name)
        self.assertEqual(results[0]["description"], store_product.description)
        self.assertEqual(results[0]["sku"], store_product.sku)
        self.assertEqual(results[0]["is_enabled"], store_product.is_enabled)
        self.assertEqual(results[0]["is_default"], store_product.is_default)

    def test_get_store_products_if_not_enabled(self):
        url = reverse("products-list")
        make(StoreProduct, is_enabled=False, _quantity=5)
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        results = response.json()["results"]
        self.assertEqual(len(results), 0)
