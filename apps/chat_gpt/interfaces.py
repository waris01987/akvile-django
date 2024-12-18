import json
import logging

from django.conf import settings
import openai


LOGGER = logging.getLogger("app")


class ChatGptRekognitionInterface:
    REKOGNITION_PROMPT = (
        "You have to parse text in brackets. Find brand of the product, "
        "it's name, ingredients and size. Please provide the answer in "
        "the JSON representation with only the following fields: 'brand', "
        "'name', 'ingredients', and 'size', without any additional text "
        'from you, even without "Here is the parsed information in JSON '
        'representation:" message. If any of this information is missing '
        "or cannot be found, make sure to include empty string in the JSON "
        'representation for the respective field. Text: "{}"'
    )

    @staticmethod
    def request_to_open_ai(messages):
        openai.api_key = settings.CHAT_GPT_API_KEY
        return openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)

    @classmethod
    def form_messages_list(cls, text):
        if not text:
            return None
        messages = []
        messages.append({"role": "system", "content": cls.REKOGNITION_PROMPT.format(text)})
        return messages

    @classmethod
    def parse_rekognition_text(cls, text):
        messages = cls.form_messages_list(text)
        if not messages:
            return None
        response = cls.request_to_open_ai(messages)
        try:
            product_info = response["choices"][0]["message"]["content"]
            return json.loads(product_info)
        except IndexError:
            return None
        except json.decoder.JSONDecodeError:
            return None
