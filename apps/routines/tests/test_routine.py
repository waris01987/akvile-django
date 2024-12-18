import datetime
from unittest.mock import patch
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message
from freezegun import freeze_time
from model_bakery.baker import make
from rest_framework import status

from apps.home.models import (
    SiteConfiguration,
    NotificationTemplate,
    NotificationTemplateTranslation,
)
from apps.questionnaire.models import UserQuestionnaire
from apps.routines.models import (
    Routine,
    EveningQuestionnaire,
    MorningQuestionnaire,
    DailyQuestionnaire,
    UserTag,
)
from apps.routines.tasks import (
    generate_reminder_message,
    send_reminder_for_daily_questionnaire,
)
from apps.users.models import UserSettings
from apps.utils.tests_utils import BaseTestCase


class RoutineTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        make(UserQuestionnaire, user=self.user)

        self.routine_1 = make(Routine, user=self.user)
        self.routine_2 = make(Routine, user=self.user)

        self.morning_questionnaire_1 = make(MorningQuestionnaire, user=self.user)
        self.morning_questionnaire_2 = make(MorningQuestionnaire, user=self.user)

        self.evening_questionnaire_1 = make(EveningQuestionnaire, user=self.user)
        self.evening_questionnaire_2 = make(EveningQuestionnaire, user=self.user)

        self.daily_questionnaire_1 = make(DailyQuestionnaire, user=self.user, water=2, hours_of_sleep=7)

    def test_routine_list(self):
        url = reverse("routines-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_routine_1 = response.json()["results"][0]
        response_routine_2 = response.json()["results"][1]

        self.assertEqual(
            response_routine_1["created_at"],
            self.routine_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response_routine_1["routine_type"], self.routine_1.routine_type)

        self.assertEqual(
            response_routine_2["created_at"],
            self.routine_2.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response_routine_2["routine_type"], self.routine_2.routine_type)

    def test_routine_list_with_date_parameter(self):
        current_time = timezone.now()
        routine_3 = make(Routine, user=self.user)
        routine_3.created_at = current_time - datetime.timedelta(days=1)
        routine_3.save()
        routine_4 = make(Routine, user=self.user)
        routine_4.created_at = current_time - datetime.timedelta(days=2)
        routine_4.save()

        query_params = {"created_at": current_time.strftime("%Y-%m-%d")}
        url = reverse("routines-list")
        response = self.get(f"{url}?{urlencode(query_params)}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 2)
        self.assertEqual(response.json()["results"][0]["routine_type"], self.routine_1.routine_type)
        self.assertEqual(
            response.json()["results"][0]["created_at"],
            self.routine_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["results"][1]["routine_type"], self.routine_2.routine_type)
        self.assertEqual(
            response.json()["results"][1]["created_at"],
            self.routine_2.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )

    def test_routine_detail(self):
        url = reverse("routines-detail", kwargs={"pk": self.routine_1.pk})
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            response.json()["created_at"],
            self.routine_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["routine_type"], self.routine_1.routine_type)

    def test_create_routine(self):
        self.query_limits["ANY POST REQUEST"] = 11
        url = reverse("routines-list")
        data = {"routine_type": "AM"}

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        routine = Routine.objects.get(user=self.user, created_at=response.json()["created_at"])
        self.assertEqual(response.json()["routine_type"], routine.routine_type)

    def test_latest_routine_returns_non_if_no_routines_exist(self):
        self.routine_1.delete()
        self.routine_2.delete()
        url = reverse("routines-latest-routine")
        response = self.get(url)
        self.assertEqual(response.json()["latest_routine"], None)

    def test_latest_routine(self):
        latest_routine = make(Routine, user=self.user)
        url = reverse("routines-latest-routine")
        response = self.get(url)
        self.assertEqual(
            response.json()["latest_routine"],
            latest_routine.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )

    def test_morning_questionnaire_list(self):
        url = reverse("morning_questionnaires-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_morning_questionnaire_1 = response.json()["results"][0]
        response_morning_questionnaire_2 = response.json()["results"][1]

        self.assertEqual(
            response_morning_questionnaire_1["created_at"],
            self.morning_questionnaire_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(
            response_morning_questionnaire_1["feeling_today"],
            self.morning_questionnaire_1.feeling_today,
        )
        self.assertEqual(
            response_morning_questionnaire_1["hours_of_sleep"],
            self.morning_questionnaire_1.hours_of_sleep,
        )
        self.assertEqual(
            response_morning_questionnaire_1["sleep_quality"],
            self.morning_questionnaire_1.sleep_quality,
        )
        self.assertEqual(
            response_morning_questionnaire_1["something_special"],
            self.morning_questionnaire_1.something_special,
        )

        self.assertEqual(
            response_morning_questionnaire_2["created_at"],
            self.morning_questionnaire_2.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(
            response_morning_questionnaire_2["feeling_today"],
            self.morning_questionnaire_2.feeling_today,
        )
        self.assertEqual(
            response_morning_questionnaire_2["hours_of_sleep"],
            self.morning_questionnaire_2.hours_of_sleep,
        )
        self.assertEqual(
            response_morning_questionnaire_2["sleep_quality"],
            self.morning_questionnaire_2.sleep_quality,
        )
        self.assertEqual(
            response_morning_questionnaire_2["something_special"],
            self.morning_questionnaire_2.something_special,
        )

    def test_morning_questionnaire_detail(self):
        url = reverse(
            "morning_questionnaires-detail",
            kwargs={"pk": self.morning_questionnaire_1.pk},
        )
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            response.json()["created_at"],
            self.morning_questionnaire_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["feeling_today"], self.morning_questionnaire_1.feeling_today)
        self.assertEqual(
            response.json()["hours_of_sleep"],
            self.morning_questionnaire_1.hours_of_sleep,
        )
        self.assertEqual(response.json()["sleep_quality"], self.morning_questionnaire_1.sleep_quality)
        self.assertEqual(
            response.json()["something_special"],
            self.morning_questionnaire_1.something_special,
        )

    def test_create_morning_questionnaire(self):
        url = reverse("morning_questionnaires-list")
        data = {
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": "VACATION",
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        morning_questionnaire = MorningQuestionnaire.objects.get(
            user=self.user, created_at=response.json()["created_at"]
        )
        self.assertEqual(response.json()["feeling_today"], morning_questionnaire.feeling_today)
        self.assertEqual(response.json()["hours_of_sleep"], morning_questionnaire.hours_of_sleep)
        self.assertEqual(response.json()["sleep_quality"], morning_questionnaire.sleep_quality)
        self.assertEqual(
            response.json()["something_special"],
            morning_questionnaire.something_special,
        )

    def test_create_morning_questionnaire_without_something_special_provided(self):
        url = reverse("morning_questionnaires-list")
        data = {
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        morning_questionnaire = MorningQuestionnaire.objects.get(
            user=self.user, created_at=response.json()["created_at"]
        )
        self.assertEqual(response.json()["something_special"], "")
        self.assertEqual(morning_questionnaire.something_special, "")

    def test_create_morning_questionnaire_with_shaving_for_menstruating_person(self):
        self.user.questionnaire.menstruating_person = True
        self.user.questionnaire.save()
        url = reverse("morning_questionnaires-list")
        data = {
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": "SHAVING",
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            "error_menstruating_person_does_not_have_shaving_option",
        )

    def test_create_morning_questionnaire_with_menstruation_for_not_menstruating_person(
        self,
    ):
        self.user.questionnaire.menstruating_person = False
        self.user.questionnaire.save()
        url = reverse("morning_questionnaires-list")
        data = {
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": "MENSTRUATION",
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            "error_not_menstruating_person_with_menstruating_persons_answers",
        )

    def test_evening_questionnaire_list(self):
        url = reverse("evening_questionnaires-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_evening_questionnaire_1 = response.json()["results"][0]
        response_evening_questionnaire_2 = response.json()["results"][1]

        self.assertEqual(
            response_evening_questionnaire_1["created_at"],
            self.evening_questionnaire_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(
            response_evening_questionnaire_1["skin_feel"],
            self.evening_questionnaire_1.skin_feel,
        )
        self.assertEqual(
            response_evening_questionnaire_1["diet_today"],
            self.evening_questionnaire_1.diet_today,
        )
        self.assertEqual(
            response_evening_questionnaire_1["water"],
            self.evening_questionnaire_1.water,
        )
        self.assertEqual(
            response_evening_questionnaire_1["life_happened"],
            self.evening_questionnaire_1.life_happened,
        )
        self.assertEqual(
            response_evening_questionnaire_1["stress_levels"],
            self.evening_questionnaire_1.stress_levels,
        )
        self.assertEqual(
            response_evening_questionnaire_1["exercise_hours"],
            self.evening_questionnaire_1.exercise_hours,
        )

        self.assertEqual(
            response_evening_questionnaire_2["created_at"],
            self.evening_questionnaire_2.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(
            response_evening_questionnaire_2["skin_feel"],
            self.evening_questionnaire_2.skin_feel,
        )
        self.assertEqual(
            response_evening_questionnaire_2["diet_today"],
            self.evening_questionnaire_2.diet_today,
        )
        self.assertEqual(
            response_evening_questionnaire_2["water"],
            self.evening_questionnaire_2.water,
        )
        self.assertEqual(
            response_evening_questionnaire_2["life_happened"],
            self.evening_questionnaire_2.life_happened,
        )
        self.assertEqual(
            response_evening_questionnaire_2["stress_levels"],
            self.evening_questionnaire_2.stress_levels,
        )
        self.assertEqual(
            response_evening_questionnaire_2["exercise_hours"],
            self.evening_questionnaire_2.exercise_hours,
        )

    def test_evening_questionnaire_detail(self):
        url = reverse(
            "evening_questionnaires-detail",
            kwargs={"pk": self.evening_questionnaire_1.pk},
        )
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            response.json()["created_at"],
            self.evening_questionnaire_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["skin_feel"], self.evening_questionnaire_1.skin_feel)
        self.assertEqual(response.json()["diet_today"], self.evening_questionnaire_1.diet_today)
        self.assertEqual(response.json()["water"], self.evening_questionnaire_1.water)
        self.assertEqual(response.json()["life_happened"], self.evening_questionnaire_1.life_happened)
        self.assertEqual(response.json()["stress_levels"], self.evening_questionnaire_1.stress_levels)
        self.assertEqual(
            response.json()["exercise_hours"],
            self.evening_questionnaire_1.exercise_hours,
        )

    def test_create_evening_questionnaire(self):
        url = reverse("evening_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "life_happened": "COFFEE",
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        evening_questionnaire = EveningQuestionnaire.objects.get(
            user=self.user, created_at=response.json()["created_at"]
        )
        self.assertEqual(response.json()["skin_feel"], evening_questionnaire.skin_feel)
        self.assertEqual(response.json()["diet_today"], evening_questionnaire.diet_today)
        self.assertEqual(response.json()["water"], evening_questionnaire.water)
        self.assertEqual(response.json()["stress_levels"], evening_questionnaire.stress_levels)
        self.assertEqual(response.json()["exercise_hours"], evening_questionnaire.exercise_hours)
        self.assertEqual(response.json()["life_happened"], evening_questionnaire.life_happened)

    def test_create_evening_questionnaire_without_life_happened_provided(self):
        url = reverse("evening_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        evening_questionnaire = EveningQuestionnaire.objects.get(
            user=self.user, created_at=response.json()["created_at"]
        )
        self.assertEqual(response.json()["life_happened"], "")
        self.assertEqual(evening_questionnaire.life_happened, "")

    def test_daily_questionnaire_list(self):
        self.query_limits["ANY GET REQUEST"] = 7
        url = reverse("daily_questionnaires-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_daily_questionnaire_1 = response.json()["results"][0]

        self.assertEqual(
            response_daily_questionnaire_1["created_at"],
            self.daily_questionnaire_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(
            response_daily_questionnaire_1["feeling_today"],
            self.daily_questionnaire_1.feeling_today,
        )
        self.assertEqual(
            response_daily_questionnaire_1["hours_of_sleep"],
            self.daily_questionnaire_1.hours_of_sleep,
        )
        self.assertEqual(
            response_daily_questionnaire_1["sleep_quality"],
            self.daily_questionnaire_1.sleep_quality,
        )
        self.assertEqual(
            response_daily_questionnaire_1["something_special"],
            self.daily_questionnaire_1.something_special,
        )
        self.assertEqual(
            response_daily_questionnaire_1["skin_feel"],
            self.daily_questionnaire_1.skin_feel,
        )
        self.assertEqual(
            response_daily_questionnaire_1["diet_today"],
            self.daily_questionnaire_1.diet_today,
        )
        self.assertEqual(response_daily_questionnaire_1["water"], self.daily_questionnaire_1.water)
        self.assertEqual(
            response_daily_questionnaire_1["life_happened"],
            self.daily_questionnaire_1.life_happened,
        )
        self.assertEqual(
            response_daily_questionnaire_1["stress_levels"],
            self.daily_questionnaire_1.stress_levels,
        )
        self.assertEqual(
            response_daily_questionnaire_1["exercise_hours"],
            self.daily_questionnaire_1.exercise_hours,
        )

    def test_daily_questionnaire_detail(self):
        self.query_limits["ANY GET REQUEST"] = 7
        url = reverse("daily_questionnaires-detail", kwargs={"pk": self.daily_questionnaire_1.pk})
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["created_at"],
            self.daily_questionnaire_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["skin_feel"], self.daily_questionnaire_1.skin_feel)
        self.assertEqual(response.json()["diet_today"], self.daily_questionnaire_1.diet_today)
        self.assertEqual(response.json()["water"], self.daily_questionnaire_1.water)
        self.assertEqual(response.json()["life_happened"], self.daily_questionnaire_1.life_happened)
        self.assertEqual(response.json()["stress_levels"], self.daily_questionnaire_1.stress_levels)
        self.assertEqual(response.json()["exercise_hours"], self.daily_questionnaire_1.exercise_hours)
        self.assertEqual(response.json()["feeling_today"], self.daily_questionnaire_1.feeling_today)
        self.assertEqual(response.json()["hours_of_sleep"], self.daily_questionnaire_1.hours_of_sleep)
        self.assertEqual(response.json()["sleep_quality"], self.daily_questionnaire_1.sleep_quality)
        self.assertEqual(
            response.json()["something_special"],
            self.daily_questionnaire_1.something_special,
        )

    def test_create_daily_questionnaire(self):
        self.query_limits["ANY POST REQUEST"] = 17
        url = reverse("daily_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "life_happened": ["COFFEE"],
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": ["VACATION"],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        daily_questionnaire = DailyQuestionnaire.objects.get(user=self.user, created_at=response.json()["created_at"])
        self.assertEqual(response.json()["feeling_today"], daily_questionnaire.feeling_today)
        self.assertEqual(response.json()["hours_of_sleep"], daily_questionnaire.hours_of_sleep)
        self.assertEqual(response.json()["sleep_quality"], daily_questionnaire.sleep_quality)
        self.assertEqual(response.json()["something_special"], daily_questionnaire.something_special)
        self.assertEqual(response.json()["skin_feel"], daily_questionnaire.skin_feel)
        self.assertEqual(response.json()["diet_today"], daily_questionnaire.diet_today)
        self.assertEqual(response.json()["water"], daily_questionnaire.water)
        self.assertEqual(response.json()["stress_levels"], daily_questionnaire.stress_levels)
        self.assertEqual(response.json()["exercise_hours"], daily_questionnaire.exercise_hours)
        self.assertEqual(response.json()["life_happened"], daily_questionnaire.life_happened)

    def test_create_daily_questionnaire_with_no_userquestionnaire(self):
        self.user.questionnaire.delete()
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "life_happened": ["COFFEE"],
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": ["VACATION"],
        }
        response = self.post(reverse("daily_questionnaires-list"), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(
            response.data,
            {"non_field_errors": ["error_user_has_no_user_questionnaire"]},
        )

    def test_create_daily_questionnaire_with_shaving_for_menstruating_person(self):
        self.user.questionnaire.menstruating_person = True
        self.user.questionnaire.save()
        url = reverse("daily_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "life_happened": ["COFFEE"],
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": ["SHAVING"],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            "error_menstruating_person_does_not_have_shaving_option",
        )

    def test_create_daily_questionnaire_with_menstruation_for_not_menstruating_person(
        self,
    ):
        self.user.questionnaire.menstruating_person = False
        self.user.questionnaire.save()
        url = reverse("daily_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "life_happened": ["COFFEE"],
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": ["MENSTRUATION"],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            "error_not_menstruating_person_with_menstruating_persons_answers",
        )

    def test_create_daily_questionnaire_without_something_special_provided(self):
        self.query_limits["ANY POST REQUEST"] = 17
        url = reverse("daily_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "life_happened": ["COFFEE"],
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        daily_questionnaire = DailyQuestionnaire.objects.get(user=self.user, created_at=response.json()["created_at"])
        self.assertEqual(response.json()["something_special"], [])
        self.assertEqual(daily_questionnaire.something_special, [])

    def test_create_daily_questionnaire_without_life_happened_provided(self):
        self.query_limits["ANY POST REQUEST"] = 17
        url = reverse("daily_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": ["VACATION"],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        daily_questionnaire = DailyQuestionnaire.objects.get(user=self.user, created_at=response.json()["created_at"])
        self.assertEqual(response.json()["life_happened"], [])
        self.assertEqual(daily_questionnaire.life_happened, [])

    def test_create_daily_questionnaire_with_multiple_answers_for_innocent_person(self):
        url = reverse("daily_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "life_happened": ["COFFEE", "INNOCENT"],
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": ["SHAVING"],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            "error_innocent_person_with_multiple_life_happened_answers",
        )

    def test_create_daily_questionnaire_with_skin_care_tags(self):
        self.query_limits["ANY POST REQUEST"] = 21
        predefined_skin_care_tag = make(UserTag, user=None, category="SKIN_CARE")
        user_defined_skin_care_tag = make(UserTag, user=self.user, category="SKIN_CARE")
        url = reverse("daily_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "life_happened": ["COFFEE"],
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": ["VACATION"],
            "tags_for_skin_care": [
                predefined_skin_care_tag.id,
                user_defined_skin_care_tag.id,
            ],
        }
        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        daily_questionnaire = DailyQuestionnaire.objects.get(user=self.user, created_at=response.json()["created_at"])
        self.assertEqual(response.json()["feeling_today"], daily_questionnaire.feeling_today)
        self.assertEqual(response.json()["hours_of_sleep"], daily_questionnaire.hours_of_sleep)
        self.assertEqual(response.json()["sleep_quality"], daily_questionnaire.sleep_quality)
        self.assertEqual(response.json()["something_special"], daily_questionnaire.something_special)
        self.assertEqual(response.json()["skin_feel"], daily_questionnaire.skin_feel)
        self.assertEqual(response.json()["diet_today"], daily_questionnaire.diet_today)
        self.assertEqual(response.json()["water"], daily_questionnaire.water)
        self.assertEqual(response.json()["stress_levels"], daily_questionnaire.stress_levels)
        self.assertEqual(response.json()["exercise_hours"], daily_questionnaire.exercise_hours)
        self.assertEqual(response.json()["life_happened"], daily_questionnaire.life_happened)
        self.assertEqual(len(response.json()["skin_care_tags"]), 2)
        self.assertEqual(
            response.json()["skin_care_tags"],
            [user_defined_skin_care_tag.name, predefined_skin_care_tag.name],
        )

    def test_create_daily_questionnaire_with_well_being_tags(self):
        self.query_limits["ANY POST REQUEST"] = 21
        predefined_well_being_tag = make(UserTag, user=None, category="WELL_BEING")
        user_defined_well_being_tag = make(UserTag, user=self.user, category="WELL_BEING")
        url = reverse("daily_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "life_happened": ["COFFEE"],
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": ["VACATION"],
            "tags_for_well_being": [
                predefined_well_being_tag.id,
                user_defined_well_being_tag.id,
            ],
        }
        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        daily_questionnaire = DailyQuestionnaire.objects.get(user=self.user, created_at=response.json()["created_at"])
        self.assertEqual(response.json()["feeling_today"], daily_questionnaire.feeling_today)
        self.assertEqual(response.json()["hours_of_sleep"], daily_questionnaire.hours_of_sleep)
        self.assertEqual(response.json()["sleep_quality"], daily_questionnaire.sleep_quality)
        self.assertEqual(response.json()["something_special"], daily_questionnaire.something_special)
        self.assertEqual(response.json()["skin_feel"], daily_questionnaire.skin_feel)
        self.assertEqual(response.json()["diet_today"], daily_questionnaire.diet_today)
        self.assertEqual(response.json()["water"], daily_questionnaire.water)
        self.assertEqual(response.json()["stress_levels"], daily_questionnaire.stress_levels)
        self.assertEqual(response.json()["exercise_hours"], daily_questionnaire.exercise_hours)
        self.assertEqual(response.json()["life_happened"], daily_questionnaire.life_happened)
        self.assertEqual(len(response.json()["well_being_tags"]), 2)
        self.assertEqual(
            response.json()["well_being_tags"],
            [user_defined_well_being_tag.name, predefined_well_being_tag.name],
        )

    def test_create_daily_questionnaire_with_nutrition_tags(self):
        self.query_limits["ANY POST REQUEST"] = 21
        predefined_nutrition_tag = make(UserTag, user=None, category="NUTRITION")
        user_defined_nutrition_tag = make(UserTag, user=self.user, category="NUTRITION")
        url = reverse("daily_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "life_happened": ["COFFEE"],
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": ["VACATION"],
            "tags_for_nutrition": [
                predefined_nutrition_tag.id,
                user_defined_nutrition_tag.id,
            ],
        }
        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        daily_questionnaire = DailyQuestionnaire.objects.get(user=self.user, created_at=response.json()["created_at"])
        self.assertEqual(response.json()["feeling_today"], daily_questionnaire.feeling_today)
        self.assertEqual(response.json()["hours_of_sleep"], daily_questionnaire.hours_of_sleep)
        self.assertEqual(response.json()["sleep_quality"], daily_questionnaire.sleep_quality)
        self.assertEqual(response.json()["something_special"], daily_questionnaire.something_special)
        self.assertEqual(response.json()["skin_feel"], daily_questionnaire.skin_feel)
        self.assertEqual(response.json()["diet_today"], daily_questionnaire.diet_today)
        self.assertEqual(response.json()["water"], daily_questionnaire.water)
        self.assertEqual(response.json()["stress_levels"], daily_questionnaire.stress_levels)
        self.assertEqual(response.json()["exercise_hours"], daily_questionnaire.exercise_hours)
        self.assertEqual(response.json()["life_happened"], daily_questionnaire.life_happened)
        self.assertEqual(len(response.json()["nutrition_tags"]), 2)
        self.assertEqual(
            response.json()["nutrition_tags"],
            [user_defined_nutrition_tag.name, predefined_nutrition_tag.name],
        )

    def test_create_daily_questionnaire_with_invalid_nutrition_tags(self):
        self.query_limits["ANY POST REQUEST"] = 18
        predefined_well_being_tag = make(UserTag, user=None, category="WELL_BEING")
        url = reverse("daily_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "life_happened": ["COFFEE"],
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": ["VACATION"],
            "tags_for_nutrition": [predefined_well_being_tag.id],
        }
        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["tags_for_nutrition"][0],
            f'Invalid pk "{predefined_well_being_tag.id}" - object does not exist.',
        )

    def test_create_daily_questionnaire_with_invalid_skin_care_tags(self):
        self.query_limits["ANY POST REQUEST"] = 18
        predefined_well_being_tag = make(UserTag, user=None, category="WELL_BEING")
        url = reverse("daily_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "life_happened": ["COFFEE"],
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": ["VACATION"],
            "tags_for_skin_care": [predefined_well_being_tag.id],
        }
        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["tags_for_skin_care"][0],
            f'Invalid pk "{predefined_well_being_tag.id}" - object does not exist.',
        )

    def test_create_daily_questionnaire_with_invalid_well_being_tags(self):
        self.query_limits["ANY POST REQUEST"] = 18
        predefined_skin_care_tag = make(UserTag, user=None, category="SKIN_CARE")
        url = reverse("daily_questionnaires-list")
        data = {
            "skin_feel": "SENSITIVE",
            "diet_today": "BALANCED",
            "water": 2,
            "stress_levels": "RELAXED",
            "exercise_hours": "TWO_HOURS",
            "life_happened": ["COFFEE"],
            "feeling_today": "LOVE_IT",
            "hours_of_sleep": 8,
            "sleep_quality": "WELL",
            "something_special": ["VACATION"],
            "tags_for_well_being": [predefined_skin_care_tag.id],
        }
        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["tags_for_well_being"][0],
            f'Invalid pk "{predefined_skin_care_tag.id}" - object does not exist.',
        )

    @freeze_time("2022-06-01")
    def test_latest_daily_questionnaire(self):
        self.query_limits["ANY GET REQUEST"] = 7
        predefined_skin_care_tag = make(UserTag, user=None, name="Predefined tag1", category="SKIN_CARE")
        user_defined_skin_care_tag = make(UserTag, user=self.user, name="User tag1", category="SKIN_CARE")
        url = reverse("daily_questionnaires-latest-questionnaire")
        today_questionnaire = make(
            DailyQuestionnaire,
            user=self.user,
            skin_feel="SENSITIVE",
            diet_today="BALANCED",
            water=2,
            stress_levels="RELAXED",
            exercise_hours="TWO_HOURS",
            life_happened=["COFFEE"],
            feeling_today="LOVE_IT",
            hours_of_sleep=8,
            sleep_quality="WELL",
            something_special=["VACATION"],
        )
        today_questionnaire.tags_for_skin_care.set([predefined_skin_care_tag.id, user_defined_skin_care_tag.id])
        today_questionnaire.save()
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["feeling_today"], today_questionnaire.feeling_today)
        self.assertEqual(response.json()["hours_of_sleep"], today_questionnaire.hours_of_sleep)
        self.assertEqual(response.json()["sleep_quality"], today_questionnaire.sleep_quality)
        self.assertEqual(response.json()["something_special"], today_questionnaire.something_special)
        self.assertEqual(response.json()["skin_feel"], today_questionnaire.skin_feel)
        self.assertEqual(response.json()["diet_today"], today_questionnaire.diet_today)
        self.assertEqual(response.json()["water"], today_questionnaire.water)
        self.assertEqual(response.json()["stress_levels"], today_questionnaire.stress_levels)
        self.assertEqual(response.json()["exercise_hours"], today_questionnaire.exercise_hours)
        self.assertEqual(response.json()["life_happened"], today_questionnaire.life_happened)
        self.assertEqual(len(response.json()["skin_care_tags"]), 2)
        self.assertEqual(
            response.json()["skin_care_tags"],
            [predefined_skin_care_tag.name, user_defined_skin_care_tag.name],
        )

    def test_no_latest_daily_questionnaire(self):
        self.query_limits["ANY GET REQUEST"] = 7
        predefined_skin_care_tag = make(UserTag, user=None, category="SKIN_CARE")
        user_defined_skin_care_tag = make(UserTag, user=self.user, category="SKIN_CARE")
        url = reverse("daily_questionnaires-latest-questionnaire")
        today_questionnaire = make(
            DailyQuestionnaire,
            user=self.user,
            skin_feel="SENSITIVE",
            diet_today="BALANCED",
            water=2,
            stress_levels="RELAXED",
            exercise_hours="TWO_HOURS",
            life_happened=["COFFEE"],
            feeling_today="LOVE_IT",
            hours_of_sleep=8,
            sleep_quality="WELL",
            something_special=["VACATION"],
        )
        today_questionnaire.tags_for_skin_care.set([predefined_skin_care_tag.id, user_defined_skin_care_tag.id])
        today_questionnaire.save()
        with freeze_time("2022-06-01"):
            response = self.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DailyQuestionNotificationTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.user_questionnaire = make(UserQuestionnaire, user=self.user)
        self.user_questionnaire.created_at = timezone.now() - datetime.timedelta(days=8)
        self.user_questionnaire.save()
        patcher = patch("apps.routines.tasks.send_push_notifications")
        self.mocked_send_push_notifications = patcher.start()
        self.addCleanup(patcher.stop)
        self.daily_questionnaire_reminder_template = make(NotificationTemplate, name="Daily Questionnaire Reminder")
        self.daily_questionnaire_reminder_template_translation = make(
            NotificationTemplateTranslation,
            template=self.daily_questionnaire_reminder_template,
            language=self.user.language,
            title="Daily Questionnaire Reminder",
            body="You did not answer your daily questionnaire today.",
        )

        self.site_config = SiteConfiguration.get_solo()
        self.site_config.daily_questionnaire_reminder_notification_template = self.daily_questionnaire_reminder_template
        self.site_config.save()
        self.user_settings = make(UserSettings, user=self.user, is_daily_questionnaire_reminder_active=True)

    def test_generate_daily_questionnaire_reminder_message(self):
        generated_message = generate_reminder_message(self.daily_questionnaire_reminder_template_translation)
        self.assertIsInstance(generated_message, Message)
        self.assertEqual(
            generated_message.notification.title,
            self.daily_questionnaire_reminder_template_translation.title,
        )
        self.assertEqual(
            generated_message.notification.body,
            self.daily_questionnaire_reminder_template_translation.body,
        )

    @freeze_time("2022-06-01 15:00:00")
    def test_daily_questionnaire_reminder_task_without_daily_questionnaire_for_today(
        self,
    ):
        make(FCMDevice, user=self.user)
        generated_message = generate_reminder_message(self.daily_questionnaire_reminder_template_translation)
        send_reminder_for_daily_questionnaire()
        user_devices = FCMDevice.objects.filter(user=self.user)
        self.assertTrue(self.mocked_send_push_notifications.called)
        self.assertEqual(
            self.mocked_send_push_notifications.call_args.args[0].count(),
            user_devices.count(),
        )
        self.assertEqual(
            self.mocked_send_push_notifications.call_args.args[0].first(),
            user_devices.first(),
        )
        message = self.mocked_send_push_notifications.call_args.kwargs["message"]
        self.assertEqual(message.notification.title, generated_message.notification.title)
        self.assertEqual(message.notification.body, generated_message.notification.body)

    @freeze_time("2022-06-01 15:00:00")
    def test_daily_questionnaire_reminder_task_with_daily_questionnaire_for_today(self):
        make(DailyQuestionnaire, user=self.user)
        make(FCMDevice, user=self.user)
        send_reminder_for_daily_questionnaire()
        self.assertFalse(self.mocked_send_push_notifications.called)

    @freeze_time("2022-06-01 15:00:00")
    def test_daily_questionnaire_reminder_task_without_notification_template(self):
        self.site_config.daily_questionnaire_reminder_notification_template = None
        self.site_config.save()
        make(FCMDevice, user=self.user)
        send_reminder_for_daily_questionnaire()
        self.assertFalse(self.mocked_send_push_notifications.called)

    @freeze_time("2022-06-01 15:00:00")
    def test_daily_questionnaire_reminder_task_with_reminder_turned_off(self):
        make(FCMDevice, user=self.user)
        self.user_settings.is_daily_questionnaire_reminder_active = False
        self.user_settings.save()
        send_reminder_for_daily_questionnaire()
        self.assertFalse(self.mocked_send_push_notifications.called)

    @freeze_time("2022-06-01 15:00:00")
    def test_daily_questionnaire_reminder_task_with_specified_eligible_users(self):
        make(FCMDevice, user=self.user)
        generated_message = generate_reminder_message(self.daily_questionnaire_reminder_template_translation)
        user_devices = FCMDevice.objects.filter(user=self.user)
        send_reminder_for_daily_questionnaire([self.user.id])
        self.assertTrue(self.mocked_send_push_notifications.called)
        self.assertEqual(
            self.mocked_send_push_notifications.call_args.args[0].count(),
            user_devices.count(),
        )
        self.assertEqual(
            self.mocked_send_push_notifications.call_args.args[0].first(),
            user_devices.first(),
        )
        message = self.mocked_send_push_notifications.call_args.kwargs["message"]
        self.assertEqual(message.notification.title, generated_message.notification.title)
        self.assertEqual(message.notification.body, generated_message.notification.body)
