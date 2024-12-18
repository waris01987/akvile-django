import logging

from django.conf import settings
import requests
from requests import Response
from requests.exceptions import InvalidHeader

LOGGER = logging.getLogger("app")


class AmazonScrapper:
    @classmethod
    def run_products_page(cls, amazon_url, pages):
        from apps.routines.models import ScrapedProduct

        asins = cls.get_products_asins_list(amazon_url, pages)
        products = cls.get_products_info_list(asins)
        scraped_products = ScrapedProduct.objects.bulk_create(products, ignore_conflicts=True)
        LOGGER.info(f"Finished importing {len(scraped_products)} products")

    @classmethod
    def call_oxylabs_api(cls, method: str, url: str, payload) -> Response:
        if not settings.OXYLABS_API_USERNAME or not settings.OXYLABS_API_PASSWORD:
            raise InvalidHeader("Oxylab authentication credentials are not set")
        auth = (settings.OXYLABS_API_USERNAME, settings.OXYLABS_API_PASSWORD)
        response = requests.request(method, url, auth=auth, json=payload)
        if response.status_code != 200:
            LOGGER.info(f"response.status_code: {response.status_code}")
            LOGGER.info("response.content: {!r}".format(response.content))
        response.raise_for_status()
        return response

    @classmethod
    def get_products_asins_list(cls, amazon_url, pages):
        asins = []
        for page in range(1, pages + 1):
            amazon_url = cls.change_page_in_url(amazon_url, page)
            response = cls.call_oxylabs_api(
                method="POST",
                url="https://realtime.oxylabs.io/v1/queries",
                payload={
                    "source": "amazon",
                    "url": amazon_url,
                    "parse": True,
                },
            )
            products_list = response.json()["results"][0]["content"]["results"]["organic"]
            for product in products_list:
                LOGGER.info(f'product.get("asin"): {product.get("asin")}')
                asins.append(product.get("asin"))
        return asins

    @staticmethod
    def change_page_in_url(url, page):
        count = 0
        for symbol in reversed(url):
            if symbol != "=":
                count += 1
                continue
            else:
                break
        new_url = url[:-count]
        new_url = new_url + str(page)
        return new_url

    @classmethod
    def get_products_info_list(cls, asins):
        from apps.routines.models import ScrapedProduct

        products_info = []
        for asin in asins:
            response = cls.call_oxylabs_api(
                method="POST",
                url="https://realtime.oxylabs.io/v1/queries",
                payload={
                    "source": "amazon_product",
                    "domain": "com",
                    "query": asin,
                    "parse": True,
                    "context": [{"key": "autoselect_variant", "value": True}],
                },
            )
            product_data = {}
            product_data["brand"] = response.json()["results"][0]["content"]["manufacturer"]
            product_data["title"] = response.json()["results"][0]["content"]["product_name"]
            product_data["source"] = "amazon"
            products_info.append(ScrapedProduct(**product_data))
        return products_info
