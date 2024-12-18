from datetime import date
import logging

from django.conf import settings
from rest_framework import exceptions, serializers

from apps.questionnaire import HoursOfSleep, Gender
from apps.questionnaire.models import UserQuestionnaire
from apps.utils.error_codes import Errors

LOGGER = logging.getLogger("app")


class UserQuestionnaireSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = UserQuestionnaire
        fields = [
            "id",
            "user",
            "skin_goal",
            "feeling_today",
            "age",
            "gender",
            "menstruating_person",
            "female_power_date",
            "contraceptive_pill",
            "stopped_birth_control_date",
            "skin_type",
            "skin_feel",
            "expectations",
            "diet_balance",
            "diet",
            "guilty_pleasures",
            "easily_stressed",
            "daily_busyness",
            "hours_of_sleep",
            "exercise_days_a_week",
            "make_up",
            "smoking_preferences",
            "is_logging_menstruation",
        ]
        extra_kwargs = {
            "menstruating_person": {"required": False},
            "female_power_date": {"required": False},
            "contraceptive_pill": {"required": False},
            "stopped_birth_control_date": {"required": False},
            "skin_type": {"required": False},
            "skin_feel": {"required": False},
            "expectations": {"required": False},
            "diet_balance": {"required": False},
            "diet": {"required": False},
            "guilty_pleasures": {"required": False},
            "easily_stressed": {"required": False},
            "daily_busyness": {"required": False},
            "hours_of_sleep": {"required": False},
            "exercise_days_a_week": {"required": False},
            "make_up": {"default": None},
            "smoking_preferences": {"required": False},
            "is_logging_menstruation": {"required": False},
        }

    def validate(self, attrs):  # noqa C901
        if self.context["request"].method == "POST" and hasattr(self.context["request"].user, "questionnaire"):
            raise exceptions.ValidationError(Errors.QUESTIONNAIRE_ALREADY_EXISTS_FOR_THIS_USER.value)

        if attrs["gender"] in {Gender.FEMALE.value, Gender.DIVERSE.value}:
            if attrs["is_logging_menstruation"] and "female_power_date" not in attrs:
                raise exceptions.ValidationError(Errors.MENSTRUATING_PERSON_HAS_TO_PROVIDE_A_POWER_DATE.value)

            if attrs["is_logging_menstruation"] and "contraceptive_pill" not in attrs:
                raise exceptions.ValidationError(
                    Errors.MENSTRUATING_PERSON_HAS_TO_PROVIDE_A_CONTRACEPTIVE_PILL_ANSWER.value
                )
        return attrs

    def validate_female_power_date(self, attr):
        if attr and attr > date.today():
            raise serializers.ValidationError(Errors.FUTURE_DATE_NOT_ALLOWED.value)
        return attr

    def validate_stopped_birth_control_date(self, attr):
        if attr and attr > date.today():
            raise serializers.ValidationError(Errors.FUTURE_DATE_NOT_ALLOWED.value)
        return attr

    def validate_hours_of_sleep(self, attr):
        literal_values = {
            HoursOfSleep.SKIPPED.value,
            HoursOfSleep.NINE_PLUS.value,
            HoursOfSleep.SEVEN_EIGHT.value,
            HoursOfSleep.FIVE_SIX.value,
            HoursOfSleep.ZERO_FOUR.value,
        }
        max_hours = settings.MAX_HOURS_OF_SLEEP
        min_hours = settings.MIN_HOURS_OF_SLEEP

        if attr not in literal_values:
            if int(attr) > max_hours or int(attr) < min_hours:
                raise exceptions.ValidationError(Errors.HOURS_OF_SLEEP_VALUE.value)
        return attr


class MakeUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserQuestionnaire
        fields = ["make_up"]
