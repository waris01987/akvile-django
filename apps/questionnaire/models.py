from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.questionnaire import (
    Age,
    ContraceptivePill,
    Diet,
    DietBalance,
    EasilyStressedAndUpset,
    ExerciseDaysAWeek,
    ExpectationsForFirstResults,
    FeelingToday,
    Gender,
    GuiltyPleasures,
    HoursOfSleep,
    SkinFeel,
    SkinGoal,
    SkinType,
    SmokingPreferences,
    DailyBusiness,
)
from apps.users.models import User
from apps.utils.models import UUIDBaseModel


class UserQuestionnaire(UUIDBaseModel):
    """This model records all answers to app's User Questionnaire.
    We decided to use one fat model to gather this data, because there are no requirements or
    current plans to configure the questions/answers, what would require additional flexibility.
    FE developers will be able to get the required translations from the Messages model.
    """

    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="questionnaire")
    skin_goal = models.CharField(
        max_length=30,
        choices=SkinGoal.get_choices(),
    )
    feeling_today = models.CharField(max_length=30, choices=FeelingToday.get_choices())
    age = models.CharField(max_length=30, choices=Age.get_choices())
    gender = models.CharField(max_length=30, choices=Gender.get_choices())
    female_power_date = models.DateField(null=True, blank=True)
    contraceptive_pill = models.CharField(
        max_length=30, choices=ContraceptivePill.get_choices(), blank=True, default=""
    )
    stopped_birth_control_date = models.DateField(null=True, blank=True)
    menstruating_person = models.BooleanField(null=True, blank=True)
    skin_type = models.CharField(max_length=30, choices=SkinType.get_choices(), blank=True, default="")
    skin_feel = models.CharField(max_length=30, choices=SkinFeel.get_choices(), blank=True, default="")
    expectations = models.CharField(
        max_length=30,
        choices=ExpectationsForFirstResults.get_choices(),
        blank=True,
        default="",
    )
    diet_balance = models.CharField(max_length=30, choices=DietBalance.get_choices(), blank=True, default="")
    diet = models.CharField(max_length=30, choices=Diet.get_choices(), blank=True, default="")
    guilty_pleasures = ArrayField(
        models.CharField(max_length=30, choices=GuiltyPleasures.get_choices()),
        default=list,
        null=True,
    )
    easily_stressed = models.CharField(
        max_length=30,
        choices=EasilyStressedAndUpset.get_choices(),
        blank=True,
        default="",
    )
    daily_busyness = models.CharField(max_length=30, choices=DailyBusiness.get_choices(), blank=True, default="")
    hours_of_sleep = models.CharField(max_length=30, choices=HoursOfSleep.get_choices(), blank=True, default="")
    exercise_days_a_week = models.CharField(
        max_length=30, choices=ExerciseDaysAWeek.get_choices(), blank=True, default=""
    )
    smoking_preferences = models.CharField(
        max_length=30, choices=SmokingPreferences.get_choices(), blank=True, default=""
    )
    is_logging_menstruation = models.BooleanField(null=True, blank=True)
    # the make up question is answered later in the app, therefore after finishing the questionnaire
    # the following field should be set to None
    make_up = models.BooleanField(null=True, default=None)

    def __str__(self):
        return f"({self.user.email} - {self.created_at})"
