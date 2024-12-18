import csv
import logging

from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponse
from django.utils import timezone
import openai
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat_gpt.models import ChatGptConfiguration, UserMessage
from apps.chat_gpt.serializers import ChatGptMessageSerializer, NewChatSerializer

LOGGER = logging.getLogger("app")


class ChatGPTBase(APIView):
    CHATGPT_PROMPTS = {
        "1,11": "get_skin_type",
        "2,21": "get_skin_improvement",
        "22,14": "choose_product",
        "22,23": "product_recommendations",
        "3,17": "get_skincare_routine",
        "4,19": "healthy_recipes",
        "4,24": "stress_management",
        "4,31": "sleep_management",
        "4,41": "activity_improvement",
    }

    @staticmethod
    def request_to_open_ai(messages):
        openai.api_key = settings.CHAT_GPT_API_KEY
        return openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)

    def modify_messages_for_chat_gpt(self, messages):
        modified_messages = []
        for message in messages:
            if message.get("preselected"):
                prompt = self.get_prompt(message.get("preselected"))
                if not prompt:
                    continue
                modified_messages.append({"role": "system", "content": prompt})
                continue
            modified_message = message.copy()
            try:
                modified_message.pop("sended_at")
            except KeyError:
                pass
            modified_messages.append(modified_message)
        return modified_messages

    def get_prompt(self, preselected):
        chat_gpt_configuration = ChatGptConfiguration.get_solo()
        prompts_values = {
            "1,11": chat_gpt_configuration.get_skin_type,
            "1,21": chat_gpt_configuration.get_skin_improvement,
            "22,14": chat_gpt_configuration.choose_product,
            "22,23": chat_gpt_configuration.product_recommendations,
            "3,17": chat_gpt_configuration.get_skincare_routine,
            "4,19": chat_gpt_configuration.healthy_recipes,
            "4,24": chat_gpt_configuration.stress_management,
            "4,31": chat_gpt_configuration.sleep_management,
            "4,41": chat_gpt_configuration.activity_improvement,
        }
        return prompts_values.get(preselected)


class ChatGPTMessage(ChatGPTBase):
    def post(self, request):
        serializer = ChatGptMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            UserMessage.objects.create(message=serializer.validated_data["message"], user=request.user)
        except IntegrityError:
            LOGGER.info(
                f"error while creating UserMessage:\nuser - {request.user}\n"
                f"message - {serializer.validated_data['message']}"
            )
        if serializer.validated_data["chat_id"] is None:
            return Response({"response": "You need to specify chat_id"}, status=400)
        else:
            chat_id = serializer.validated_data["chat_id"]
            try:
                messages = request.user.chat_gpt_history[chat_id] + [
                    {
                        "role": "user",
                        "content": serializer.validated_data["message"],
                        "sended_at": timezone.now().strftime("%m/%d/%Y, %H:%M:%S"),
                    }
                ]
                modified_messages = self.modify_messages_for_chat_gpt(messages)
            except KeyError:
                return Response({"response": "Wrong chat_id"}, status=400)
        response = self.request_to_open_ai(modified_messages)
        messages.append(response["choices"][0]["message"])
        request.user.update_chat_history(messages, chat_id)
        return Response({"response": response["choices"][0]["message"]["content"]}, status=200)


class NewChat(ChatGPTBase):
    def post(self, request):
        serializer = NewChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        LOGGER.info(f"new chat data: {serializer.validated_data}")
        try:
            UserMessage.objects.create(message=serializer.validated_data["message"], user=request.user)
        except IntegrityError:
            LOGGER.info(
                f"error while creating UserMessage:\nuser - {request.user}\n"
                f"message - {serializer.validated_data['message']}"
            )
        messages = [
            {
                "role": "user",
                "content": serializer.validated_data["message"],
                "sended_at": timezone.now().strftime("%m/%d/%Y, %H:%M:%S"),
            }
        ]
        if serializer.validated_data.get("preselected"):
            messages.append(
                {
                    "sended_at": timezone.now().strftime("%m/%d/%Y, %H:%M:%S"),
                    "preselected": serializer.validated_data["preselected"],
                }
            )
        modified_messages = self.modify_messages_for_chat_gpt(messages)
        chat_id = len(request.user.chat_gpt_history) + 1
        LOGGER.info(f"modified_messages: {modified_messages}")
        response = self.request_to_open_ai(modified_messages)
        messages.append(response["choices"][0]["message"])
        request.user.update_chat_history(messages, chat_id)
        return Response({"response": response["choices"][0]["message"]["content"]}, status=200)


class Chats(APIView):
    def get(self, request):
        return Response({"chats": request.user.chat_gpt_history}, status=200)


class ExportChats(APIView):
    def get(self, request):
        if not request.user.is_superuser:
            return Response({"error": "you are not superuser"})
        messages = UserMessage.objects.filter().values("user_id", "message")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="export.csv"'
        writer = csv.DictWriter(response, fieldnames=["user", "message"])
        writer.writeheader()
        for message in messages:
            writer.writerow({"user": message.get("user_id"), "message": message.get("message")})
        return response
