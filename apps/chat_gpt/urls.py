from django.urls import path

from apps.chat_gpt.views import ChatGPTMessage, Chats, NewChat, ExportChats

urlpatterns = [
    path("new_message/", ChatGPTMessage.as_view(), name="new_chat_gpt_message"),
    path("new_chat/", NewChat.as_view(), name="new_chat"),
    path("chats/", Chats.as_view(), name="chats"),
    path("export_chats/", ExportChats.as_view(), name="export_chats"),
]
