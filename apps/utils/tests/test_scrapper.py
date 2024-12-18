from unittest.mock import patch

from django.conf import settings
from django.urls import reverse
from requests import Response

from apps.routines.models import ScrapedProduct
from apps.utils.scrape import AmazonScrapper
from apps.utils.tests_utils import BaseTestCase


class TestAmazonScrapper(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.login(**self.credentials)

    def fake_interface_call(self):
        return

    @patch.object(AmazonScrapper, "run_products_page", fake_interface_call)
    def test_amazon_view(self):
        url = reverse("import_scrapped_products")
        data = {"amazon_url": "amazon.com", "pages": 4}

        response = self.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "done"})

    @patch.object(AmazonScrapper, "run_products_page", fake_interface_call)
    def test_amazon_view_with_no_url(self):
        url = reverse("import_scrapped_products")
        data = {"pages": 4}

        response = self.post(url, data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"amazon_url": ["This field is required."]})

    @patch.object(AmazonScrapper, "run_products_page", fake_interface_call)
    def test_amazon_view_with_no_page(self):
        url = reverse("import_scrapped_products")
        data = {"amazon_url": "amazon.com"}

        response = self.post(url, data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"pages": ["This field is required."]})

    def fake_asins_list(self, amazon_url):
        return ["qweasd", "zxcrty"]

    def fake_get_products_info_list(self):
        return [
            ScrapedProduct(
                **{
                    "brand": "garnier",
                    "title": "garnier moisturizer cream",
                    "source": "amazon",
                }
            ),
            ScrapedProduct(
                **{
                    "brand": "cerave",
                    "title": "cerave moisturizer cream",
                    "source": "amazon",
                }
            ),
        ]

    @patch.object(AmazonScrapper, "get_products_asins_list", fake_asins_list)
    @patch.object(AmazonScrapper, "get_products_info_list", fake_get_products_info_list)
    def test_amazon_scrapper_interface(self):
        AmazonScrapper.run_products_page(amazon_url="some.url", pages=5)
        scrapped_products = ScrapedProduct.objects.filter(source="amazon").values("brand", "title")
        self.assertEqual(
            list(scrapped_products),
            [
                {"brand": "garnier", "title": "garnier moisturizer cream"},
                {"brand": "cerave", "title": "cerave moisturizer cream"},
            ],
        )

    @staticmethod
    def fake_call_oxylabs_api(method, url, payload):
        return Response()

    @staticmethod
    def fake_json():
        return {"results": [{"content": {"results": {"organic": [{"asin": "qwe"}, {"asin": "asd"}]}}}]}

    @patch.object(AmazonScrapper, "call_oxylabs_api", fake_call_oxylabs_api)
    @patch.object(Response, "json", fake_json)
    def test_get_products_asins_list(self):
        asins = AmazonScrapper.get_products_asins_list(amazon_url="some.url", pages=2)
        self.assertEqual(asins, ["qwe", "asd", "qwe", "asd"])

    @patch.object(Response, "json", fake_json)
    def test_call_oxylabs_api(self):
        settings.OXYLABS_API_USERNAME = "qwe"
        settings.OXYLABS_API_PASSWORD = "qwe"
        response = AmazonScrapper.call_oxylabs_api(method="GET", url="http://some.com", payload={"data": "data"})
        self.assertEqual(response.status_code, 200)

    def test_change_page_in_url(self):
        url = AmazonScrapper.change_page_in_url("some.com/param=1&page=3", 4)
        self.assertEqual(url, "some.com/param=1&page=4")

    @staticmethod
    def fake_products_info_json():
        return {
            "results": [
                {
                    "content": {
                        "manufacturer": "garnier",
                        "product_name": "garnier moisturizer cream",
                    }
                }
            ]
        }

    @patch.object(AmazonScrapper, "call_oxylabs_api", fake_call_oxylabs_api)
    @patch.object(Response, "json", fake_products_info_json)
    def test_get_products_info_list(self):
        result = AmazonScrapper.get_products_info_list(["qwe"])
        product = result[0]
        self.assertEqual(product.brand, "garnier")
        self.assertEqual(product.title, "garnier moisturizer cream")
        self.assertEqual(product.source, "amazon")
