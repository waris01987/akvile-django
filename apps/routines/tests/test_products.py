import io
from unittest.mock import patch
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from model_bakery.baker import make
from parameterized import parameterized_class, parameterized
from PIL import Image
from rest_framework import status

from apps.chat_gpt.interfaces import ChatGptRekognitionInterface
from apps.routines import ProductType
from apps.routines.models import DailyProductGroup, DailyProduct, ScrapedProduct
from apps.text_rekognition.script import TextRekognition
from apps.users.models import User
from apps.utils.tests_utils import BaseTestCase


class DailyProductBaseTest(BaseTestCase):
    def generate_image(self):
        generated_file = io.BytesIO()
        image = Image.new("RGBA", size=(100, 100), color=(155, 0, 0))
        image.save(generated_file, "png")
        generated_file.name = f"{uuid.uuid4().hex}test.png"
        generated_file.seek(0)
        return generated_file

    def generate_scrapped_product(self):
        unique_id = uuid.uuid4().hex
        data = {
            "title": f"{unique_id} Some title",
            "brand": f"{unique_id} Some brand",
            "ingredients": f"{unique_id} Some ingredients",
            "url": "url.com",
        }
        return data

    def generate_product(self, *args, **kwargs):
        data = {
            "type": kwargs.pop("product_type"),
        }
        data.update(kwargs)
        return data

    def fake_json_data(self):
        return [
            ["1946576767", 1, 1],
            [
                [],
                [
                    None,
                    [
                        None,
                        None,
                        None,
                        None,
                        [],
                        None,
                        None,
                        None,
                        [
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            [
                                [
                                    [],
                                    "Visual matches",
                                    None,
                                    2147483647,
                                    None,
                                    None,
                                    None,
                                    [
                                        [114096, 114095, 0, "114096.0", -1],
                                        None,
                                        None,
                                        "Show less",
                                        "See more",
                                        "Show less Similar images",
                                        "See more Similar images",
                                    ],
                                    [],
                                    [None, None, None, None, True],
                                    None,
                                    [114095, None, 1, "114095.1", -1],
                                    [
                                        [
                                            [
                                                "https://encrypted-tbn2.gstatic.com/images?q=tbn:ANd"
                                                "9GcT73CLyouQTZSgtpdPQvI6yvYqWj45-uyJm8CsD4lZLXloM6Izt",
                                                168,
                                                300,
                                                None,
                                                None,
                                                [162539, None, 0, "162539.0", -1],
                                                None,
                                                None,
                                                None,
                                                None,
                                                "1mEh8uAIFc8DVM",
                                            ],
                                            0.56,
                                            None,
                                            "Garnier SkinActive Acqua micellare Tutto in 1 - INCI Beauty",
                                            None,
                                            "https://incibeauty.com/en/produit/3600541358492",
                                            [52162, None, 0, "52162.0", 0],
                                            "incibeauty.com",
                                            None,
                                            None,
                                            None,
                                            "https://incibeauty.com/en/produit/3600541358492",
                                            1,
                                            None,
                                            "incibeauty.com",
                                            [
                                                "https://encrypted-tbn3.gstatic.com/favicon-tbn?q=tbn:A"
                                                "Nd9GcQmm9E4ZqPXKAzRc9dSUqB13-03cD_Eey5RAZW4keakVJcm5B"
                                                "I0C6U7MvlsClN-EyFhN9ox1uSnS90Dcm-iFieQYShOn2JJN1Yzl3ignsg6613lYg"
                                            ],
                                            None,
                                            None,
                                            None,
                                            "Garnier SkinActive Acqua micellare Tutto in 1 - INCI Beaut"
                                            "y from incibeauty.com",
                                            [162538, None, 0, "162538.0", -1],
                                        ]
                                    ],
                                    None,
                                    None,
                                    None,
                                    False,
                                    [],
                                ]
                            ],
                        ],
                    ],
                ],
            ],
        ]


class DailyProductGroupTest(DailyProductBaseTest):
    url = reverse("daily_product_groups-list")
    types = list(dict(ProductType.get_choices()).keys())
    errors = {
        "duplicate_product_type": "errors_duplicate_product_type",
        "non_valid_choice": '"{}" is not a valid choice.',
        "required_field": "This field is required.",
        "non_blank_field": "This field may not be blank.",
        "integer_field": "A valid integer is required.",
        "product_group_already_exists": "errors_product_group_already_exists",
        "no_image_provided": "no_image_provided",
    }

    def fake_rekognition_request(self):
        return "Garnier SkinActive Acqua micellare Tutto in 1 - INCI Beauty"

    def to_multipart(self, name, data):
        result = {}
        for i, entry in enumerate(data):
            for key, value in entry.items():
                result[f"{name}[{i}]{key}"] = value
        return result

    def encode_to(self, data):
        new_data = {}
        for key, value in data.items():
            if isinstance(value, list):
                new_data.update(self.to_multipart(key, value))
            else:
                new_data[key] = value
        return new_data

    def generate_products(self, products):
        result = []
        for product in products:
            args, kwargs = [], {}
            if isinstance(product, dict):
                kwargs = product
            result.append(self.generate_product(*args, **kwargs))
        return result

    def generate_product_group(self, *args, **kwargs):
        products = kwargs.pop("products_data", [])
        data = {"country": "USA", "products": self.generate_products(products)}
        data.update(kwargs)
        if args:
            data = {field: data[field] for field in args}
        return data

    def get_instance_products(self, product_group):
        instance_products = []
        instance_types = []
        for product in product_group.products.all():
            product_data = {
                field: getattr(product, field)
                for field in [
                    "id",
                    "name",
                    "brand",
                    "ingredients",
                    "size",
                    "type",
                    "product_info",
                ]
            }
            product_data["image"] = product.image.url if product.image else ""
            product_data["product_info"] = {
                "id": product.product_info.id if product.product_info else None,
                "title": product.product_info.title if product.product_info else None,
                "brand": product.product_info.brand if product.product_info else None,
                "ingredients": product.product_info.ingredients if product.product_info else None,
                "url": product.product_info.url if product.product_info else None,
            }
            instance_products.append(product_data)
            instance_types.append(product.type)
        return instance_products, instance_types

    def check_products(self, response_products, instance_products, request_products, instance_types):
        response_types = []
        for response_product, instance_product, request_product in zip(
            response_products, instance_products, request_products
        ):
            response_image = response_product.pop("image")
            instance_image = instance_product.pop("image", None)
            request_image = request_product.pop("image", None)
            response_product.pop("image_parsing_success")
            self.assertDictEqual(dict(response_product), instance_product)
            response_types.append(response_product["type"])
            if request_image:
                self.assertIn(instance_image, response_image)
            else:
                self.assertEqual(instance_image, "")
                self.assertIsNone(response_image)

    def check_product_group(self, request_data, response):
        product_group = DailyProductGroup.objects.all()
        self.assertEqual(len(product_group), 1)
        product_group = product_group.first()
        response_products = response.pop("products")
        request_products = request_data.pop("products")
        instance_data = {field: getattr(product_group, field) for field in ["id", "country"]}
        request_data["id"] = product_group.id
        self.assertDictEqual(instance_data, request_data)
        self.assertDictEqual(response, request_data)
        return product_group, response_products, request_products

    def call_api(self, request_data, status_code, count=0):
        request_data = self.encode_to(request_data)
        self.assertEqual(DailyProductGroup.objects.count(), count)
        response = self.authorize().post(self.url, data=request_data, format="multipart")
        self.assertEqual(response.status_code, status_code, response.json())
        return response

    def success_flow(self, request_data):
        response = self.call_api(request_data, status.HTTP_201_CREATED)
        product_group, response_products, request_products = self.check_product_group(request_data, response.json())
        instance_products, instance_types = self.get_instance_products(product_group)
        self.check_products(response_products, instance_products, request_products, instance_types)

    def error_flow(self, request_data, expected, count=0):
        response = self.call_api(request_data, status.HTTP_400_BAD_REQUEST, count)
        self.assertEqual(response.json(), expected)
        self.assertEqual(DailyProductGroup.objects.count(), count)

    def test_get_daily_product_groups(self):
        self.image = SimpleUploadedFile("icon.png", b"file_content")
        user = User.objects.create_user(**{**self.user_data, **{"email": "something" + self.user_data["email"]}})

        product_group = make(DailyProductGroup, user=self.user)
        for product_type in self.types:
            make(DailyProduct, group=product_group, type=product_type, image=self.image)

        product_group_2 = make(DailyProductGroup, user=user)
        for product_type in self.types:
            make(DailyProduct, group=product_group_2, type=product_type, image=self.image)

        response = self.authorize().get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected = {field: getattr(product_group, field) for field in ["id", "country"]}
        expected_products, _ = self.get_instance_products(product_group)
        products = response.data.pop("products")
        self.assertDictEqual(response.data, expected)

        for product, expected_product in zip(products, expected_products):
            product_image = product.pop("image")
            expected_image = expected_product.pop("image")
            if expected_product.get("name"):
                expected_product["image_parsing_success"] = True
            else:
                expected_product["image_parsing_success"] = False
            self.assertDictEqual(dict(product), expected_product)
            self.assertIn(expected_image, product_image)

    @patch.object(TextRekognition, "run_bytes", fake_rekognition_request)
    def test_create_daily_product_group(self):
        request_data = self.generate_product_group(
            products_data=[
                {
                    "product_type": ProductType.CLEANSER.value,
                    "image": self.generate_image(),
                }
            ]
        )
        self.success_flow(request_data)

    @patch.object(TextRekognition, "run_bytes", fake_rekognition_request)
    def test_create_daily_product_group_with_duplicate_types(self):
        request_data = self.generate_product_group(
            products_data=[
                {
                    "product_type": ProductType.CLEANSER.value,
                    "image": self.generate_image(),
                },
                {
                    "image": self.generate_image(),
                    "product_type": ProductType.CLEANSER.value,
                },
            ]
        )
        self.error_flow(request_data, [self.errors["duplicate_product_type"]])

    @patch.object(TextRekognition, "run_bytes", fake_rekognition_request)
    def test_create_daily_product_group_with_non_existing_type(self):
        non_existing_type = "Other type"
        request_data = self.generate_product_group(products_data=[{"product_type": non_existing_type}])
        self.error_flow(
            request_data,
            {"products": [{"type": [self.errors["non_valid_choice"].format(non_existing_type)]}]},
        )

    @patch.object(TextRekognition, "run_bytes", fake_rekognition_request)
    def test_create_daily_product_group_with_empty_type(self):
        request_data = self.generate_product_group(products_data=[{"product_type": ""}])
        self.error_flow(
            request_data,
            {"products": [{"type": [self.errors["non_valid_choice"].format("")]}]},
        )

    def test_create_daily_product_group_with_empty_product(self):
        request_data = self.generate_product_group(products=[{}])
        self.error_flow(request_data, {"products": [self.errors["required_field"]]})

    def test_create_daily_product_group_without_products(self):
        request_data = self.generate_product_group(products=[])
        self.error_flow(request_data, {"products": [self.errors["required_field"]]})

    def test_create_daily_product_group_with_less_data(self):
        request_data = self.generate_product_group(
            products_data=[
                {"product_type": ProductType.CLEANSER.value},
                {"product_type": ProductType.TREATMENT.value},
            ]
        )
        self.error_flow(
            request_data,
            {
                "products": [
                    {"image": [self.errors["no_image_provided"]]},
                    {"image": [self.errors["no_image_provided"]]},
                ]
            },
        )

    @patch.object(TextRekognition, "run_bytes", fake_rekognition_request)
    def test_create_daily_product_group_with_required_data(self):
        request_data = self.generate_product_group(
            products_data=[
                {
                    "product_type": ProductType.CLEANSER.value,
                    "image": self.generate_image(),
                }
            ]
        )
        self.success_flow(request_data)

    @patch.object(TextRekognition, "run_bytes", fake_rekognition_request)
    def test_create_daily_product_group_with_blank_data(self):
        request_data = self.generate_product_group(
            country="",
            products_data=[
                {"product_type": "", "image": self.generate_image()},
            ],
        )
        self.error_flow(
            request_data,
            {
                "country": [self.errors["non_blank_field"]],
                "products": [{"type": [self.errors["non_valid_choice"].format("")]}],
            },
        )

    @patch.object(TextRekognition, "run_bytes", fake_rekognition_request)
    def test_create_daily_product_group_with_only_blank_product_type_data(self):
        request_data = self.generate_product_group(
            "products",
            products_data=[
                {"product_type": ""},
            ],
        )
        self.error_flow(
            request_data,
            {
                "country": [self.errors["required_field"]],
                "products": [{"type": [self.errors["non_valid_choice"].format("")]}],
            },
        )

    @patch.object(TextRekognition, "run_bytes", fake_rekognition_request)
    def test_create_daily_product_group_without_data(self):
        request_data = {}
        self.error_flow(
            request_data,
            {
                "country": [self.errors["required_field"]],
                "products": [self.errors["required_field"]],
            },
        )

    @patch.object(TextRekognition, "run_bytes", fake_rekognition_request)
    def test_create_daily_product_group_duplicate(self):
        self.image = SimpleUploadedFile("icon.png", b"file_content")
        product_group = make(DailyProductGroup, user=self.user)
        for product_type in self.types:
            make(DailyProduct, group=product_group, type=product_type, image=self.image)
        request_data = self.generate_product_group(
            products_data=[
                {
                    "product_type": ProductType.CLEANSER.value,
                    "image": self.generate_image(),
                },
                {
                    "product_type": ProductType.TREATMENT.value,
                    "image": self.generate_image(),
                },
            ]
        )
        self.error_flow(
            request_data,
            {"non_field_errors": [self.errors["product_group_already_exists"]]},
            1,
        )


class DailyProductTest(DailyProductBaseTest):
    detail_url = "daily_products-detail"
    list_url = reverse("daily_products-list")
    errors = {"not_found": "Not found."}

    def fake_rekognition_request(self):
        return "Garnier SkinActive Acqua micellare Tutto in 1 - INCI Beauty"

    def setUp(self):
        super().setUp()
        self.image = SimpleUploadedFile("icon.png", b"file_content")

    def check_data(self, product, response):
        expected_product = {
            field: getattr(product, field) for field in ["id", "name", "brand", "ingredients", "size", "type"]
        }
        expected_product["product_info"] = {
            "id": product.product_info.id if product.product_info else None,
            "title": product.product_info.title if product.product_info else None,
            "brand": product.product_info.brand if product.product_info else None,
            "ingredients": product.product_info.ingredients if product.product_info else None,
            "url": product.product_info.url if product.product_info else None,
        }
        if expected_product.get("name"):
            expected_product["image_parsing_success"] = True
        else:
            expected_product["image_parsing_success"] = False

        response["product_info"] = dict(response.get("product_info"))

        try:
            self.assertIn(product.image.url, response.pop("image"))
        except ValueError:
            self.assertIn(product.image, None)
        self.assertDictEqual(dict(response), expected_product)

    def call_api(self, status_code, increment_id=0, user=None, url=None):
        product_group = make(DailyProductGroup, user=user or self.user)
        scrapped_product = make(ScrapedProduct, **self.generate_scrapped_product())
        product = make(
            DailyProduct,
            group=product_group,
            type=ProductType.CLEANSER.value,
            image=self.image,
            product_info=scrapped_product,
        )
        if not url:
            url = reverse(self.detail_url, args=[product.id + increment_id])
        response = self.authorize().get(url)
        self.assertEqual(response.status_code, status_code)
        return response, product

    def test_get_product(self):
        response, product = self.call_api(status.HTTP_200_OK)
        self.check_data(product, response.data)

    def test_get_non_existing_product(self):
        response, product = self.call_api(status.HTTP_404_NOT_FOUND, 1)
        self.assertDictEqual(response.data, {"detail": self.errors["not_found"]})

    def test_get_different_users_product(self):
        user = User.objects.create_user(**{**self.user_data, **{"email": "something" + self.user_data["email"]}})
        response, product = self.call_api(status.HTTP_404_NOT_FOUND, 0, user)
        self.assertDictEqual(response.data, {"detail": self.errors["not_found"]})

    def test_get_products(self):
        response, product = self.call_api(status.HTTP_200_OK, url=self.list_url)
        self.assertEqual(len(response.data["results"]), 1)
        self.check_data(product, response.data["results"][0])

    def fake_google_lens_request(self):
        return "Garnier SkinActive Acqua micellare Tutto in 1 - INCI Beauty"

    def fake_openai_request(self):
        return {
            "id": "chatcmpl-7dfCWC4zzjAsNfJa9VItV1yYQwED9",
            "object": "chat.completion",
            "created": 1689687524,
            "model": "gpt-3.5-turbo-0613",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": '{"brand": "", "name": "SkinActive  Tutto", "ingredients": "", "size": ""}',
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 9, "total_tokens": 20},
        }

    @patch.object(TextRekognition, "run_bytes", fake_rekognition_request)
    @patch.object(ChatGptRekognitionInterface, "request_to_open_ai", fake_openai_request)
    def test_query_google_lens(self):
        product_group = make(DailyProductGroup, user=self.user)
        scrapped_product = make(ScrapedProduct, id=None, title="some_title")
        product = make(
            DailyProduct,
            group=product_group,
            type=ProductType.CLEANSER.value,
            image=self.image,
            product_info=scrapped_product,
        )
        product.image = SimpleUploadedFile("icon1.png", b"file_content1")
        product.save()
        self.assertEqual(product.name, "Garnier SkinActive Acqua micellare Tutto in 1 - INCI Beauty")

    def fake_failed_google_lens_request(self):
        return ""

    def fake_fail_rekognition_request(self):
        return ""

    @patch.object(TextRekognition, "run_bytes", fake_rekognition_request)
    @patch.object(ChatGptRekognitionInterface, "request_to_open_ai", fake_openai_request)
    def test_update_product(self):
        product_group = make(DailyProductGroup, user=self.user)
        product = make(
            DailyProduct,
            group=product_group,
            type=ProductType.CLEANSER.value,
            image=self.image,
            _fill_optional=True,
        )
        self.assertTrue(all([getattr(product, field) for field in DailyProduct.CLEARABLE_FIELDS]))
        data = self.generate_product(product_type=ProductType.CLEANSER.value, image=self.generate_image())
        old_image = product.image

        response = self.authorize().put(reverse(self.detail_url, args=[product.id]), data=data, format="multipart")
        product.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(any([getattr(product, field) for field in DailyProduct.CLEARABLE_FIELDS]))
        self.assertEqual(product.type, ProductType.CLEANSER.value)
        self.assertNotEqual(product.image, old_image)
        self.check_data(product, response.data)

    def test_check_existing_products(self):
        scrapped_product_1 = make(
            ScrapedProduct,
            id=1,
            title="Garnier SkinActive Acqua micellare Tutto in 1",
            brand="Garnier",
            ingredients="water, something",
            url="www.url1.com",
        )
        make(
            ScrapedProduct,
            id=3,
            title="Garnier mens deodorant",
            brand="Garnier",
            ingredients="water, something",
            url="www.url1.com",
        )
        make(
            ScrapedProduct,
            id=4,
            title="Garnier SkinActive Acqua in 1",
            brand="Garnier",
            ingredients="water, something",
            url="www.url1.com",
        )
        make(
            ScrapedProduct,
            id=2,
            title="SUSANNE KAUFMANN Hypersensitive Hydrating Face Gel 50ml",
            brand="SUSANNE KAUFMANN",
            ingredients="Aqua (Water), Pentylene Glycol, Glycerin, Propanediol, Saccharide Isomerate",
            url="www.url2.com",
        )
        lens_title = "Garnier SkinActive Acqua micellare Tutto in 1 - INCI Beauty from incibeauty.com"
        result = DailyProduct().get_similar_scrapped_product_by_title(lens_title)
        self.assertEqual(scrapped_product_1.id, result.id)

    @patch.object(TextRekognition, "run_bytes", fake_fail_rekognition_request)
    def test_update_daily_products_names_task(self):
        product_group = make(DailyProductGroup, user=self.user)
        scrapped_product = make(ScrapedProduct, id=None, title="some_title")
        product = make(
            DailyProduct,
            group=product_group,
            type=ProductType.CLEANSER.value,
            image=self.image,
            product_info=scrapped_product,
        )
        product.image = SimpleUploadedFile("icon1.png", b"file_content1")
        product.save()
        self.assertEqual(product.image_parse_fail, 1)

    def make_product_for_test(self, daily_product_params):
        product_group = make(DailyProductGroup, user=self.user)
        return make(
            DailyProduct,
            group=product_group,
            type=ProductType.CLEANSER.value,
            image=self.image,
            name="product1",
            **daily_product_params,
        )

    def test_connect_daily_products_to_scrapped_task(self):
        from apps.routines.tasks import connect_scrapped_product_to_daily_product

        self.make_product_for_test(daily_product_params={})
        scrapped_product = make(ScrapedProduct, title="product1")
        connect_scrapped_product_to_daily_product()
        updated_product = DailyProduct.objects.get(name="product1")
        self.assertEqual(updated_product.product_info, scrapped_product)

    def test_connect_daily_products_to_scrapped_task_with_no_product(self):
        from apps.routines.tasks import connect_scrapped_product_to_daily_product

        self.make_product_for_test(daily_product_params={})
        connect_scrapped_product_to_daily_product()
        updated_product = DailyProduct.objects.get(name="product1")
        self.assertEqual(updated_product.product_info, None)
        self.assertEqual(updated_product.connect_scrapped_fail, 1)

    def test_set_satisfaction_score_to_product_without_easy_to_use_score(self):
        product = self.make_product_for_test(daily_product_params={})
        self.authorize().post(
            reverse("daily_product_review"),
            data={
                "product_id": product.id,
                "review_score": 3,
                "satisfaction_score": 3,
                "preference_score": 3,
                "efficiency_score": 3,
                "accessibility_score": 3,
                "cost_score": 3,
            },
        )
        product1 = DailyProduct.objects.get(id=product.id)
        self.assertEqual(product1.review_score, 3)
        self.assertEqual(product1.satisfaction_score, 3)
        self.assertEqual(product1.preference_score, 3)
        self.assertEqual(product1.efficiency_score, 3)
        self.assertEqual(product1.accessibility_score, 3)
        self.assertEqual(product1.cost_score, 3)
        self.assertEqual(product1.easy_to_use_score, 3)

    def test_set_satisfaction_score_to_product_with_easy_to_use_score(self):
        product = self.make_product_for_test(daily_product_params={})
        self.authorize().post(
            reverse("daily_product_review"),
            data={
                "product_id": product.id,
                "review_score": 3,
                "satisfaction_score": 3,
                "preference_score": 3,
                "efficiency_score": 3,
                "accessibility_score": 3,
                "cost_score": 3,
                "easy_to_use_score": 3,
            },
        )
        product1 = DailyProduct.objects.get(id=product.id)
        self.assertEqual(product1.review_score, 3)
        self.assertEqual(product1.satisfaction_score, 3)
        self.assertEqual(product1.preference_score, 3)
        self.assertEqual(product1.efficiency_score, 3)
        self.assertEqual(product1.accessibility_score, 3)
        self.assertEqual(product1.cost_score, 3)
        self.assertEqual(product1.easy_to_use_score, 3)

    def test_set_big_satisfaction_score_to_product(self):
        product = self.make_product_for_test(daily_product_params={})
        response = self.authorize().post(
            reverse("daily_product_review"),
            data={
                "product_id": product.id,
                "review_score": 6,
                "satisfaction_score": 6,
                "preference_score": 6,
                "efficiency_score": 6,
                "accessibility_score": 6,
                "cost_score": 6,
                "easy_to_use_score": 6,
            },
        )
        self.assertEqual(
            response.json(),
            {
                "review_score": ["review score must be between 0 and 5"],
                "satisfaction_score": ["satisfaction score must be between 0 and 5"],
                "preference_score": ["preference score must be between 0 and 5"],
                "efficiency_score": ["efficiency score must be between 0 and 5"],
                "accessibility_score": ["accessibility score must be between 0 and 5"],
                "cost_score": ["cost score must be between 0 and 5"],
                "easy_to_use_score": ["easy_to_use score must be between 0 and 5"],
            },
        )

    def test_set_low_satisfaction_score_to_product(self):
        product = self.make_product_for_test(daily_product_params={})
        response = self.authorize().post(
            reverse("daily_product_review"),
            data={
                "product_id": product.id,
                "review_score": -1,
                "satisfaction_score": -1,
                "preference_score": -1,
                "efficiency_score": -1,
                "accessibility_score": -1,
                "cost_score": -1,
                "easy_to_use_score": -1,
            },
        )
        self.assertEqual(
            response.json(),
            {
                "review_score": ["review score must be between 0 and 5"],
                "satisfaction_score": ["satisfaction score must be between 0 and 5"],
                "preference_score": ["preference score must be between 0 and 5"],
                "efficiency_score": ["efficiency score must be between 0 and 5"],
                "accessibility_score": ["accessibility score must be between 0 and 5"],
                "cost_score": ["cost score must be between 0 and 5"],
                "easy_to_use_score": ["easy_to_use score must be between 0 and 5"],
            },
        )

    def test_set_satisfaction_score_to_product_with_no_id(self):
        self.make_product_for_test(daily_product_params={})
        response = self.authorize().post(
            reverse("daily_product_review"),
            data={
                "review_score": 3,
                "satisfaction_score": 3,
                "preference_score": 3,
                "efficiency_score": 3,
                "accessibility_score": 3,
                "cost_score": 3,
                "easy_to_use_score": 3,
            },
        )
        self.assertEqual(response.json(), {"product_id": ["This field is required."]})

    @patch.object(TextRekognition, "run_bytes", fake_rekognition_request)
    def test_daily_product_create(self):
        make(DailyProductGroup, user=self.user)
        data = {"type": "TREATMENT", "image": self.generate_image()}
        response = self.authorize().post(reverse("daily_product_create-list"), data=data, format="multipart")
        self.assertEqual(
            response.data.get("name"),
            "Garnier SkinActive Acqua micellare Tutto in 1 - INCI Beauty",
        )

    @patch.object(TextRekognition, "run_bytes", fake_rekognition_request)
    def test_daily_product_create_with_no_group(self):
        data = {"type": "TREATMENT", "image": self.generate_image()}
        response = self.authorize().post(reverse("daily_product_create-list"), data=data, format="multipart")
        self.assertEqual(
            response.data,
            {"non_field_errors": ["errors_user_doesnt_have_product_group"]},
        )


@parameterized_class(
    [
        {"url": reverse("daily-product-brand-autocomplete"), "field": "brand"},
        {"url": reverse("daily-product-name-autocomplete"), "field": "name"},
    ]
)
class DailyProductAutocompleteTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.login(**self.credentials)

        self.product_group = make(DailyProductGroup, user=self.user)
        self.product_1 = make(
            DailyProduct,
            group=self.product_group,
            type=ProductType.CLEANSER.value,
            brand="Svyturio",
            name="Extra",
        )
        self.product_2 = make(
            DailyProduct,
            group=self.product_group,
            type=ProductType.MOISTURIZER.value,
            brand="Kalnapilio",
            name="Extra",
        )
        self.product_3 = make(
            DailyProduct,
            group=self.product_group,
            type=ProductType.TREATMENT.value,
            brand="Svyturio",
            name="Baltas",
        )

    def get_product_data(self, product, create=False):
        return self.get_data(getattr(product, self.field), create=create)

    def get_data(self, text, create=False):
        data = {"id": text, "text": text}
        if create:
            data["text"] = f'Create "{text}"'
            data["create_id"] = True
        return data

    def unauthorize(self):
        self.user.is_staff = False
        self.user.is_superuser = False
        self.user.save()

    def unauthenticate(self):
        self.client.logout()

    def sort(self, data):
        return sorted(data, key=lambda item: item["text"])

    def check_response(self, response, expected):
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())

        results = response.json().pop("results")

        self.assertEqual(response.json(), {})
        self.assertEqual(self.sort(results), self.sort(expected))

    def test_get_all(self):
        response = self.client.get(self.url)

        self.check_response(response, list(map(self.get_product_data, [self.product_2, self.product_3])))

    def test_get_filter(self):
        response = self.client.get(f"{self.url}?q={getattr(self.product_1, self.field)}")

        self.check_response(
            response,
            [
                self.get_product_data(self.product_1),
                self.get_product_data(self.product_1, True),
            ],
        )

    def test_post_create(self):
        response = self.client.post(self.url, data={"text": "Naujas"}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(response.json(), self.get_data("Naujas"))

    @parameterized.expand(
        [
            ["unauthorize", "get", {}],
            ["unauthenticate", "get", {}],
            [
                "unauthorize",
                "post",
                {"data": {"text": "Naujas"}, "format": "multipart"},
            ],
            [
                "unauthenticate",
                "post",
                {"data": {"text": "Naujas"}, "format": "multipart"},
            ],
        ]
    )
    def test_non_admin_access(self, method, action, params):
        getattr(self, method)()

        response = getattr(self.client, action)(self.url, **params)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.json())
        self.assertEqual(response.json(), {"detail": "Admin access only"})


class DailyProductStatisticTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.login(**self.credentials)

        self.image = SimpleUploadedFile("icon.png", b"file_content")
        self.product_group = make(DailyProductGroup, user=self.user)
        self.scrapped_product_1 = make(ScrapedProduct, title="title1", brand="brand1")
        self.product_1 = make(
            DailyProduct,
            group=self.product_group,
            type=ProductType.CLEANSER.value,
            brand="Svyturio",
            name="Extra",
            image=self.image,
        )
        self.product_2 = make(
            DailyProduct,
            group=self.product_group,
            type=ProductType.MOISTURIZER.value,
            brand="Kalnapilio",
            name="Extra",
        )
        self.product_3 = make(
            DailyProduct,
            group=self.product_group,
            type=ProductType.TREATMENT.value,
            brand="Svyturio",
            name="Baltas",
            image=self.image,
        )

    def test_statistic(self):
        response = self.client.get(reverse("get_scrapped_products_statistics"))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(
            response.json(),
            {
                "statistic": {
                    "all_products": 3,
                    "with_photo": 2,
                    "with_title": 3,
                    "with_scrapped_product": 0,
                }
            },
        )
