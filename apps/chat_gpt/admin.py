from django.contrib import admin
from solo.admin import SingletonModelAdmin
from tabbed_admin import TabbedModelAdmin

from apps.chat_gpt.models import ChatGptConfiguration, UserMessage


@admin.register(ChatGptConfiguration)
class ChatGptConfigurationAdmin(TabbedModelAdmin, SingletonModelAdmin):
    tab_chat_gpt_prompts = (
        (
            None,
            {
                "fields": (
                    (
                        "get_skin_type",
                        "get_skin_improvement",
                        "choose_product",
                        "product_recommendations",
                        "get_skincare_routine",
                        "healthy_recipes",
                        "stress_management",
                        "sleep_management",
                        "activity_improvement",
                    ),
                )
            },
        ),
    )

    tabs = [
        ("Prompts", tab_chat_gpt_prompts),
    ]


@admin.register(UserMessage)
class UserMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "message",
        "category",
        "user",
        "created_at",
    )
    raw_id_fields = ["user"]
