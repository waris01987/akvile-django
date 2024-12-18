from rest_framework import serializers


class ChatGptMessageSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)
    chat_id = serializers.CharField(required=False)


class NewChatSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)
    preselected = serializers.CharField(required=False)
