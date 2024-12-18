from django.db import models
from solo.models import SingletonModel

from apps.users.models import User
from apps.utils.models import BaseModel


class ChatGptConfiguration(SingletonModel):
    get_skin_type = models.TextField(blank=True, default="")
    get_skin_improvement = models.TextField(blank=True, default="")
    choose_product = models.TextField(blank=True, default="")
    product_recommendations = models.TextField(blank=True, default="")
    get_skincare_routine = models.TextField(blank=True, default="")
    healthy_recipes = models.TextField(blank=True, default="")
    stress_management = models.TextField(blank=True, default="")
    sleep_management = models.TextField(blank=True, default="")
    activity_improvement = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "ChatGpt Configuration"


class UserMessage(BaseModel):
    message = models.TextField(blank=True, default="")
    category = models.CharField(max_length=200, blank=True, default="")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category_updated = models.BooleanField(default=False)

    class Meta:
        verbose_name = "ChatGpt user message"
