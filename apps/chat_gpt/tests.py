from unittest.mock import patch

from django.urls import reverse

from apps.chat_gpt.interfaces import ChatGptRekognitionInterface
from apps.chat_gpt.models import ChatGptConfiguration
from apps.chat_gpt.views import ChatGPTBase
from apps.utils.tests_utils import BaseTestCase


class ChatGptTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        chat_gpt_configuration = ChatGptConfiguration.get_solo()
        chat_gpt_configuration.get_skin_type = "get_skin_type"
        chat_gpt_configuration.get_skin_improvement = "get_skin_improvement"
        chat_gpt_configuration.choose_product = "choose_product"
        chat_gpt_configuration.product_recommendations = "product_recommendations"
        chat_gpt_configuration.get_skincare_routine = "get_skincare_routine"
        chat_gpt_configuration.healthy_recipes = "healthy_recipes"
        chat_gpt_configuration.stress_management = "stress_management"
        chat_gpt_configuration.sleep_management = "sleep_management"
        chat_gpt_configuration.activity_improvement = "activity_improvement"
        chat_gpt_configuration.save()

    def fake_chat_gpt_request(self, messages):
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
                        "content": "Hello, my friend! How can I assist you today?",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 9, "total_tokens": 20},
        }

    @patch.object(ChatGPTBase, "request_to_open_ai", fake_chat_gpt_request)
    def test_new_chat_gpt_view(self):
        data = {"message": "Hello chat gpt", "preselected": "1,11"}
        response = self.authorize().post(reverse("new_chat"), data=data, format="multipart")
        self.assertEqual(
            response.data.get("response"),
            "Hello, my friend! How can I assist you today?",
        )

    @patch.object(ChatGPTBase, "request_to_open_ai", fake_chat_gpt_request)
    def test_continue_chat_gpt_view(self):
        data = {
            "message": "I'm okay. How is the weather today in London?",
            "chat_id": 1,
        }
        self.user.chat_gpt_history = {
            1: [
                {
                    "role": "user",
                    "content": "Hello chat gpt",
                    "sended_at": "12/24/2018, 04:59:31",
                }
            ]
        }
        self.user.save()
        response = self.authorize().post(reverse("new_chat_gpt_message"), data=data, format="multipart")
        self.assertEqual(
            response.data.get("response"),
            "Hello, my friend! How can I assist you today?",
        )

    @patch.object(ChatGPTBase, "request_to_open_ai", fake_chat_gpt_request)
    def test_wrong_chat_id(self):
        data = {
            "message": "I'm okay. How is the weather today in London?",
            "chat_id": 2,
        }
        self.user.chat_gpt_history = {1: [{"role": "user", "content": "Hello chat gpt"}]}
        self.user.save()
        response = self.authorize().post(reverse("new_chat_gpt_message"), data=data, format="multipart")
        self.assertEqual(response.data.get("response"), "Wrong chat_id")


class ChatGptRekognitionInterfaceTestCase(BaseTestCase):
    def test_form_messages_list_no_text(self):
        messages = ChatGptRekognitionInterface.form_messages_list(text=None)
        self.assertEqual(messages, None)

    def test_form_messages_list_with_empty_string(self):
        messages = ChatGptRekognitionInterface.form_messages_list(text="")
        self.assertEqual(messages, None)

    def test_form_messages_list(self):
        messages = ChatGptRekognitionInterface.form_messages_list(
            text="Garnier SkinActive Acqua micellare Tutto in 1 - INCI Beauty 100ml"
        )
        self.assertEqual(
            messages,
            [
                {
                    "role": "system",
                    "content": "You have to parse text in brackets. Find brand of the product, it's name, ingredients"
                    " and size. Please provide the answer in the JSON representation with only the following"
                    " fields: 'brand', 'name', 'ingredients', and 'size', without any additional "
                    'text from you, even without "Here is the parsed information in JSON representation:" '
                    "message. If any of this information is missing or cannot be found, make sure to "
                    "include empty string in the JSON representation for the respective field. "
                    'Text: "Garnier SkinActive Acqua micellare Tutto in 1 - INCI Beauty 100ml"',
                }
            ],
        )

    def fake_chat_gpt_request(self):
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
                        "content": '{"brand": "Garnier", "name": "SkinActive Acqua micellare Tutto 1 - INCI Beauty", '
                        '"ingredients": "", "size": "100ml"}',
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 9, "total_tokens": 20},
        }

    def fake_failed_chat_gpt_request(self):
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
                        "content": "Sorry I cannot find anything",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 9, "total_tokens": 20},
        }

    @patch.object(ChatGptRekognitionInterface, "request_to_open_ai", fake_chat_gpt_request)
    def test_parse_rekognition_text(self):
        messages = ChatGptRekognitionInterface.parse_rekognition_text(
            text="Garnier SkinActive Acqua micellare Tutto in 1 - INCI Beauty 100ml"
        )
        self.assertEqual(
            messages,
            {
                "brand": "Garnier",
                "name": "SkinActive Acqua micellare Tutto 1 - INCI Beauty",
                "ingredients": "",
                "size": "100ml",
            },
        )

    @patch.object(ChatGptRekognitionInterface, "request_to_open_ai", fake_failed_chat_gpt_request)
    def test_parse_rekognition_text_with_failed_response(self):
        messages = ChatGptRekognitionInterface.parse_rekognition_text(
            text="Garnier SkinActive Acqua micellare Tutto in 1 - INCI Beauty 100ml"
        )
        self.assertEqual(messages, None)
