import logging
from unittest.mock import patch

from apps.lens.google_lens_request import GoogleLensApi
from apps.utils.tests_utils import BaseTestCase

LOGGER = logging.getLogger("app")


class GoogleLensBaseTest(BaseTestCase):
    def setUp(self):
        self.expected_result = [
            {
                "google_image": "https://encrypted-tbn2.gstatic.com/images?q=tb"
                "n:ANd9GcQS7mZ8JoSM_Fj1u-WO-iLjQW0QvOwq4LsOyE1VtnxiyNlGuXoA",
                "product_link": "https://www.beautech.com.sg/clearing-sebum-mask",
                "title": "Clearing Sebum Mask",
                "redirect_url": "https://www.beautech.com.sg/clearing-sebum-mask",
                "redirect_name": "beautech.com.sg",
            },
            {
                "google_image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9Gc"
                "QyVbol-x4k0wHS7VoaoEjC6F3AmLTwrS93j_MNlqEMkGNnrTZZ",
                "product_link": "https://www.ubuy.vn/en/product/PABZU8K-klapp-psc-oil-fre"
                "e-lotion-problem-skin-care-for-oily-skin-acne-skin-75ml",
                "title": "KLAPP PSC Oil Free Lotion Problem Skin Care for Oily | Ubuy Vietnam",
                "redirect_url": "https://www.ubuy.vn/en/product/PABZU8K-klapp-psc-oil-fre"
                "e-lotion-problem-skin-care-for-oily-skin-acne-skin-75ml",
                "redirect_name": "ubuy.vn",
            },
        ]

    @staticmethod
    def fake_image_check(img_url, headers):
        return True

    @staticmethod
    def fake_request_to_google_lens(url, headers):
        return {}

    @staticmethod
    def fake_extract_data(soup):
        return [
            {
                "google_image": "https://encrypted-tbn2.gstatic.com/images?q=tb"
                "n:ANd9GcQS7mZ8JoSM_Fj1u-WO-iLjQW0QvOwq4LsOyE1VtnxiyNlGuXoA",
                "product_link": "https://www.beautech.com.sg/clearing-sebum-mask",
                "title": "Clearing Sebum Mask",
                "redirect_url": "https://www.beautech.com.sg/clearing-sebum-mask",
                "redirect_name": "beautech.com.sg",
            },
            {
                "google_image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9Gc"
                "QyVbol-x4k0wHS7VoaoEjC6F3AmLTwrS93j_MNlqEMkGNnrTZZ",
                "product_link": "https://www.ubuy.vn/en/product/PABZU8K-klapp-psc-oil-fre"
                "e-lotion-problem-skin-care-for-oily-skin-acne-skin-75ml",
                "title": "KLAPP PSC Oil Free Lotion Problem Skin Care for Oily | Ubuy Vietnam",
                "redirect_url": "https://www.ubuy.vn/en/product/PABZU8K-klapp-psc-oil-fre"
                "e-lotion-problem-skin-care-for-oily-skin-acne-skin-75ml",
                "redirect_name": "ubuy.vn",
            },
        ]

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
                                        ],
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

    def mocked_requests_get(*args, **kwargs):
        class MockResponse:
            def __init__(self, json_data, status_code):
                self.json_data = json_data
                self.status_code = status_code

            def json(self):
                return self.json_data

        if kwargs.get("url") == "http://image_host.com/img.png":
            return MockResponse({"key1": "value1"}, 200)
        elif kwargs.get("url") == "https://lens.google.com/uploadbyurl?url={}".format("http://image_host.com/img.png"):
            return MockResponse({"key2": "value2"}, 200)

        return MockResponse(None, 404)

    @patch("requests.get", side_effect=mocked_requests_get)
    @patch.object(GoogleLensApi, "get_json_from_response", fake_json_data)
    def test_query_google_lens(self, request_mock):
        result = GoogleLensApi.query_google_lens("http://image_host.com/img.png")
        self.assertEqual(result, "Garnier SkinActive Acqua micellare Tutto in 1 - INCI Beauty")

    @patch.object(GoogleLensApi, "request_to_google_lens", fake_request_to_google_lens)
    def test_request_to_google_lens(self):
        result = GoogleLensApi.request_to_google_lens(url="https://url.com", headers="headers")
        self.assertEqual(result, {})

    @patch.object(GoogleLensApi, "check_image_url", fake_image_check)
    def test_check_image_url(self):
        result = GoogleLensApi.check_image_url(img_url="https://url.com", headers="headers")
        self.assertEqual(result, True)
