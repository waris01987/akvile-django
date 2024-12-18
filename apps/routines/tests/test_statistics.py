import datetime
import io
from unittest.mock import patch

from django.core.files import File
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from freezegun import freeze_time
from model_bakery.baker import make
from parameterized import parameterized
from PIL import Image
from rest_framework import status

from apps.home.models import (
    PredictionTemplate,
    PredictionTemplateTranslation,
)
from apps.questionnaire.models import UserQuestionnaire
from apps.routines import (
    HealthCareEventTypes,
    SleepQuality,
    PredictionTypes,
    PredictionCategories,
)
from apps.routines.models import (
    Routine,
    DailyQuestionnaire,
    DailyStatistics,
    Prediction,
    HealthCareEvent,
)
from apps.utils.tests_utils import BaseTestCase


class DailyStatisticsTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        make(UserQuestionnaire, user=self.user)

    def test_statistics_list(self):
        make(Routine, user=self.user, routine_type="AM")
        make(Routine, user=self.user, routine_type="PM")
        daily_statistics_1 = make(DailyStatistics, user=self.user)
        url = reverse("statistics-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_statistics_1 = response.json()["results"][0]
        self.assertEqual(response_statistics_1["id"], daily_statistics_1.id)
        self.assertEqual(response_statistics_1["skin_care"], daily_statistics_1.skin_care)
        self.assertEqual(response_statistics_1["well_being"], daily_statistics_1.well_being)
        self.assertEqual(response_statistics_1["nutrition"], daily_statistics_1.nutrition)
        self.assertEqual(response_statistics_1["date"], daily_statistics_1.date.strftime("%Y-%m-%d"))

    def test_statistics_without_routine(self):
        url = reverse("statistics-list")
        response_1 = self.get(url)
        self.assertEqual(response_1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_1.json()["results"]), 0)
        daily_questionnaire = make(DailyQuestionnaire, user=self.user)
        statistics_from_db = DailyStatistics.objects.filter(
            user=self.user, date=daily_questionnaire.created_at.date()
        ).first()
        response_2 = self.get(url)
        self.assertEqual(response_2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_2.json()["results"]), 1)
        response_statistics = response_2.json()["results"][0]
        self.assertEqual(statistics_from_db.routine_count_status, "NOT_COUNTED")
        self.assertEqual(response_statistics["id"], statistics_from_db.id)
        self.assertEqual(response_statistics["skin_care"], statistics_from_db.skin_care)
        self.assertEqual(response_statistics["well_being"], statistics_from_db.well_being)
        self.assertEqual(response_statistics["nutrition"], statistics_from_db.nutrition)
        self.assertEqual(response_statistics["date"], statistics_from_db.date.strftime("%Y-%m-%d"))

    def test_statistics_with_only_morning_routine(self):
        url = reverse("statistics-list")
        response_1 = self.get(url)
        self.assertEqual(response_1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_1.json()["results"]), 0)
        make(Routine, user=self.user, routine_type="AM")
        daily_questionnaire = make(DailyQuestionnaire, user=self.user)
        statistics_from_db = DailyStatistics.objects.filter(
            user=self.user, date=daily_questionnaire.created_at.date()
        ).first()
        response_2 = self.get(url)
        self.assertEqual(response_2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_2.json()["results"]), 1)
        response_statistics = response_2.json()["results"][0]
        self.assertEqual(statistics_from_db.routine_count_status, "ONLY_AM_COUNTED")
        self.assertEqual(response_statistics["id"], statistics_from_db.id)
        self.assertEqual(response_statistics["skin_care"], statistics_from_db.skin_care)
        self.assertEqual(response_statistics["well_being"], statistics_from_db.well_being)
        self.assertEqual(response_statistics["nutrition"], statistics_from_db.nutrition)
        self.assertEqual(response_statistics["date"], statistics_from_db.date.strftime("%Y-%m-%d"))

    def test_statistics_with_only_evening_routine(self):
        url = reverse("statistics-list")
        response_1 = self.get(url)
        self.assertEqual(response_1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_1.json()["results"]), 0)
        make(Routine, user=self.user, routine_type="PM")
        daily_questionnaire = make(DailyQuestionnaire, user=self.user)
        statistics_from_db = DailyStatistics.objects.filter(
            user=self.user, date=daily_questionnaire.created_at.date()
        ).first()
        response_2 = self.get(url)
        self.assertEqual(response_2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_2.json()["results"]), 1)
        response_statistics = response_2.json()["results"][0]
        self.assertEqual(statistics_from_db.routine_count_status, "ONLY_PM_COUNTED")
        self.assertEqual(response_statistics["id"], statistics_from_db.id)
        self.assertEqual(response_statistics["skin_care"], statistics_from_db.skin_care)
        self.assertEqual(response_statistics["well_being"], statistics_from_db.well_being)
        self.assertEqual(response_statistics["nutrition"], statistics_from_db.nutrition)
        self.assertEqual(response_statistics["date"], statistics_from_db.date.strftime("%Y-%m-%d"))

    def test_statistics_with_both_morning_and_evening_routines(self):
        url = reverse("statistics-list")
        response_1 = self.get(url)
        self.assertEqual(response_1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_1.json()["results"]), 0)
        make(Routine, user=self.user, routine_type="AM")
        make(Routine, user=self.user, routine_type="PM")
        daily_questionnaire = make(DailyQuestionnaire, user=self.user)
        statistics_from_db = DailyStatistics.objects.filter(
            user=self.user, date=daily_questionnaire.created_at.date()
        ).first()
        response_2 = self.get(url)
        self.assertEqual(response_2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_2.json()["results"]), 1)
        response_statistics = response_2.json()["results"][0]
        self.assertEqual(statistics_from_db.routine_count_status, "COUNTING_COMPLETED")
        self.assertEqual(response_statistics["id"], statistics_from_db.id)
        self.assertEqual(response_statistics["skin_care"], statistics_from_db.skin_care)
        self.assertEqual(response_statistics["well_being"], statistics_from_db.well_being)
        self.assertEqual(response_statistics["nutrition"], statistics_from_db.nutrition)
        self.assertEqual(response_statistics["date"], statistics_from_db.date.strftime("%Y-%m-%d"))

    def test_statistics_update_after_morning_routine_creation(self):
        url = reverse("statistics-list")
        daily_questionnaire = make(DailyQuestionnaire, user=self.user)
        statistics_from_db = DailyStatistics.objects.filter(
            user=self.user, date=daily_questionnaire.created_at.date()
        ).first()
        response_1 = self.get(url)
        self.assertEqual(response_1.status_code, status.HTTP_200_OK)
        response_statistics_1 = response_1.json()["results"][0]
        self.assertEqual(statistics_from_db.routine_count_status, "NOT_COUNTED")
        self.assertEqual(response_statistics_1["id"], statistics_from_db.id)
        self.assertEqual(response_statistics_1["skin_care"], statistics_from_db.skin_care)
        self.assertEqual(response_statistics_1["well_being"], statistics_from_db.well_being)
        self.assertEqual(response_statistics_1["nutrition"], statistics_from_db.nutrition)
        self.assertEqual(response_statistics_1["date"], statistics_from_db.date.strftime("%Y-%m-%d"))

        make(Routine, user=self.user, routine_type="AM")
        response_2 = self.get(url)
        self.assertEqual(response_2.status_code, status.HTTP_200_OK)
        updated_statistics_from_db = DailyStatistics.objects.filter(
            user=self.user, date=daily_questionnaire.created_at.date()
        ).first()
        response_statistics_2 = response_2.json()["results"][0]
        self.assertEqual(updated_statistics_from_db.routine_count_status, "ONLY_AM_COUNTED")
        self.assertLess(statistics_from_db.skin_care, response_statistics_2["skin_care"])

    def test_statistics_update_after_evening_routine_creation(self):
        url = reverse("statistics-list")
        daily_questionnaire = make(DailyQuestionnaire, user=self.user)
        statistics_from_db = DailyStatistics.objects.filter(
            user=self.user, date=daily_questionnaire.created_at.date()
        ).first()
        response_1 = self.get(url)
        self.assertEqual(response_1.status_code, status.HTTP_200_OK)
        response_statistics_1 = response_1.json()["results"][0]
        self.assertEqual(statistics_from_db.routine_count_status, "NOT_COUNTED")
        self.assertEqual(response_statistics_1["id"], statistics_from_db.id)
        self.assertEqual(response_statistics_1["skin_care"], statistics_from_db.skin_care)
        self.assertEqual(response_statistics_1["well_being"], statistics_from_db.well_being)
        self.assertEqual(response_statistics_1["nutrition"], statistics_from_db.nutrition)
        self.assertEqual(response_statistics_1["date"], statistics_from_db.date.strftime("%Y-%m-%d"))

        make(Routine, user=self.user, routine_type="PM")
        response_2 = self.get(url)
        self.assertEqual(response_2.status_code, status.HTTP_200_OK)
        updated_statistics_from_db = DailyStatistics.objects.filter(
            user=self.user, date=daily_questionnaire.created_at.date()
        ).first()
        response_statistics_2 = response_2.json()["results"][0]
        self.assertEqual(updated_statistics_from_db.routine_count_status, "ONLY_PM_COUNTED")
        self.assertLess(statistics_from_db.skin_care, response_statistics_2["skin_care"])

    def test_statistics_update_after_with_routine_count_completion(self):
        make(Routine, user=self.user, routine_type="AM")
        url = reverse("statistics-list")
        daily_questionnaire = make(DailyQuestionnaire, user=self.user)
        statistics_from_db = DailyStatistics.objects.filter(
            user=self.user, date=daily_questionnaire.created_at.date()
        ).first()
        response_1 = self.get(url)
        self.assertEqual(response_1.status_code, status.HTTP_200_OK)
        response_statistics_1 = response_1.json()["results"][0]
        self.assertEqual(statistics_from_db.routine_count_status, "ONLY_AM_COUNTED")
        self.assertEqual(response_statistics_1["id"], statistics_from_db.id)
        self.assertEqual(response_statistics_1["skin_care"], statistics_from_db.skin_care)
        self.assertEqual(response_statistics_1["well_being"], statistics_from_db.well_being)
        self.assertEqual(response_statistics_1["nutrition"], statistics_from_db.nutrition)
        self.assertEqual(response_statistics_1["date"], statistics_from_db.date.strftime("%Y-%m-%d"))

        make(Routine, user=self.user, routine_type="PM")
        response_2 = self.get(url)
        self.assertEqual(response_2.status_code, status.HTTP_200_OK)
        updated_statistics_from_db = DailyStatistics.objects.filter(
            user=self.user, date=daily_questionnaire.created_at.date()
        ).first()
        response_statistics_2 = response_2.json()["results"][0]
        self.assertEqual(updated_statistics_from_db.routine_count_status, "COUNTING_COMPLETED")
        self.assertLess(statistics_from_db.skin_care, response_statistics_2["skin_care"])

    @freeze_time("2022-6-3")
    def test_statistics_overview(self):
        today = datetime.datetime.now()
        first_day_of_current_month = today.replace(day=1)
        last_day_of_previous_month = first_day_of_current_month - datetime.timedelta(days=1)
        last_five_days_of_previous_month = [
            last_day_of_previous_month - datetime.timedelta(days=idx) for idx in range(1, 6)
        ]
        for day in last_five_days_of_previous_month:
            make(
                DailyStatistics,
                user=self.user,
                date=day.date(),
                skin_care=30,
                well_being=40,
                nutrition=50,
            )
        last_month_avg = 40
        first_five_days_of_current_month = [
            first_day_of_current_month + datetime.timedelta(days=idx) for idx in range(1, 6)
        ]
        for day in first_five_days_of_current_month:
            make(
                DailyStatistics,
                user=self.user,
                date=day.date(),
                skin_care=50,
                well_being=60,
                nutrition=70,
            )
        current_month_avg = 60
        url = reverse("statistics-overview")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.json()
        self.assertEqual(result["current_month_average"], current_month_avg)
        self.assertEqual(result["last_month_average"], last_month_avg)
        self.assertEqual(result["today_average"], 60)
        self.assertEqual(result["yesterday_average"], 60)

    def test_statistics_overview_with_no_data(self):
        url = reverse("statistics-overview")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.json()
        self.assertEqual(result["current_month_average"], 0)
        self.assertEqual(result["last_month_average"], 0)
        self.assertEqual(result["today_average"], 0)
        self.assertEqual(result["yesterday_average"], 0)

    @parameterized.expand(
        [
            [["COFFEE", "ALCOHOL", "JUNK_FOOD_AND_SWEETS"], 80],
            [["INNOCENT"], 100],
            [["COFFEE"], 85],
            [["COFFEE", "ALCOHOL"], 80],
            [["COFFEE", "JUNK_FOOD_AND_SWEETS"], 80],
            [[], 75],
        ]
    )
    @freeze_time("2022-6-3")
    def test_statistics_with_multiple_answers_for_life_happened(self, life_happened_answer, nutrition_score):
        make(
            DailyQuestionnaire,
            user=self.user,
            skin_feel="NORMAL",
            diet_today="BALANCED",
            water=3,
            stress_levels="RELAXED",
            exercise_hours="TWO_HOURS",
            life_happened=life_happened_answer,
            feeling_today="LOVE_IT",
            hours_of_sleep=8,
            sleep_quality="WELL",
        )
        daily_statistics = DailyStatistics.objects.filter(user=self.user).first()
        self.assertEqual(daily_statistics.skin_care, 50)
        self.assertEqual(daily_statistics.well_being, 95)
        self.assertEqual(daily_statistics.nutrition, nutrition_score)
        self.assertEqual(daily_statistics.date, datetime.datetime.now().date())

    @parameterized.expand(
        [
            ["2022-04-01", 0, 0, 0, 0],
            ["2022-05-02", 75, 0, 90, 60],
            ["2022-05-30", 75, 0, 0, 0],
            ["2022-06-04", 70, 75, 70, 60],
            ["2022-06-15", 70, 75, 0, 0],
        ]
    )
    def test_filtering_statistics_overview(
        self, current_date, current_month_avg, last_month_avg, today_avg, yesterday_avg
    ):
        make(
            DailyStatistics,
            user=self.user,
            date=datetime.date(year=2022, month=5, day=1),
            skin_care=50,
            well_being=60,
            nutrition=70,
        )
        make(
            DailyStatistics,
            user=self.user,
            date=datetime.date(year=2022, month=5, day=2),
            skin_care=80,
            well_being=90,
            nutrition=100,
        )

        make(
            DailyStatistics,
            user=self.user,
            date=datetime.date(year=2022, month=6, day=1),
            skin_care=50,
            well_being=60,
            nutrition=70,
        )
        make(
            DailyStatistics,
            user=self.user,
            date=datetime.date(year=2022, month=6, day=2),
            skin_care=100,
            well_being=90,
            nutrition=80,
        )
        make(
            DailyStatistics,
            user=self.user,
            date=datetime.date(year=2022, month=6, day=3),
            skin_care=60,
            well_being=60,
            nutrition=60,
        )
        make(
            DailyStatistics,
            user=self.user,
            date=datetime.date(year=2022, month=6, day=4),
            skin_care=80,
            well_being=70,
            nutrition=60,
        )
        url = reverse("statistics-overview")
        query_params = {"date": current_date}
        response = self.get(f"{url}?{urlencode(query_params)}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.json()
        self.assertEqual(result["current_month_average"], current_month_avg)
        self.assertEqual(result["last_month_average"], last_month_avg)
        self.assertEqual(result["today_average"], today_avg)
        self.assertEqual(result["yesterday_average"], yesterday_avg)


class PredictionTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.today = datetime.datetime.now(datetime.timezone.utc)
        previous_day = self.today - datetime.timedelta(days=1)
        self.next_day = self.today + datetime.timedelta(days=1)
        self.dates = [previous_day.date(), self.today.date(), self.next_day.date()]
        self.user_questionnaire = make(UserQuestionnaire, user=self.user)
        self.user_questionnaire.created_at = self.today - datetime.timedelta(days=8)
        self.user_questionnaire.save()

    @staticmethod
    def get_image_file(name="test.png", ext="png", size=(50, 50), color=(256, 0, 0)):
        file_obj = io.BytesIO()
        image = Image.new("RGBA", size=size, color=color)
        image.save(file_obj, ext)
        file_obj.seek(0)
        return File(file_obj, name=name)

    def test_routine_prediction(self):
        for day in range(-7, 0):
            date = self.today + datetime.timedelta(days=day)
            am_routine = make(Routine, user=self.user, routine_type="AM")
            am_routine.created_at = date
            am_routine.save()
            pm_routine = make(Routine, user=self.user, routine_type="PM")
            pm_routine.created_at = date
            pm_routine.save()

        make(
            DailyQuestionnaire,
            user=self.user,
            skin_feel="GREASY",
            diet_today="BALANCED",
            water=2,
            stress_levels="EXTREME",
            exercise_hours="TWO_HOURS",
            life_happened=["SMOKING"],
            feeling_today="LOVE_IT",
            hours_of_sleep=9,
            sleep_quality="LOVE_IT",
            something_special=["SHAVING"],
            _quantity=2,
        )
        make(
            DailyQuestionnaire,
            user=self.user,
            skin_feel="NORMAL",
            diet_today="UNBALANCED",
            water=1,
            stress_levels="MODERATE",
            exercise_hours="ZERO",
            life_happened=["INNOCENT"],
            feeling_today="BAD",
            hours_of_sleep=5,
            sleep_quality="MEHHH",
            something_special=["VACATION"],
            _quantity=2,
        )
        daily_questionnaire_5 = make(
            DailyQuestionnaire,
            user=self.user,
            skin_feel="GREASY",
            diet_today="BALANCED",
            water=2,
            stress_levels="EXTREME",
            exercise_hours="TWO_HOURS",
            life_happened=["SMOKING"],
            feeling_today="LOVE_IT",
            hours_of_sleep=9,
            sleep_quality="LOVE_IT",
            something_special=["SHAVING"],
        )
        daily_questionnaire_5.created_at = self.next_day
        daily_questionnaire_5.save()
        prediction = Prediction.objects.filter(user=self.user).latest("created_at")
        self.assertEqual(prediction.prediction_type, "ROUTINE_DONE")

    def test_daily_questionnaire_prediction(self):
        daily_questionnaire = make(
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
        prediction = Prediction.objects.filter(user=self.user).last()
        self.assertEqual(prediction.user, daily_questionnaire.user)
        self.assertEqual(prediction.date, daily_questionnaire.created_at.date())
        self.assertEqual(prediction.prediction_type, "DAILY_QUESTIONNAIRE_SKIPPED")

    def test_daily_questionnaire_or_routine_predictions_do_not_repeat(self):
        for day in range(-7, 0):
            date = self.today + datetime.timedelta(days=day)
            am_routine = make(Routine, user=self.user, routine_type="AM")
            am_routine.created_at = date
            am_routine.save()
            pm_routine = make(Routine, user=self.user, routine_type="PM")
            pm_routine.created_at = date
            pm_routine.save()

        daily_questionnaire_1 = make(
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
        daily_questionnaire_1.created_at = self.today + datetime.timedelta(days=1)
        daily_questionnaire_1.save()

        daily_questionnaire_2 = make(
            DailyQuestionnaire,
            user=self.user,
            skin_feel="GREASY",
            diet_today="UNBALANCED",
            water=0,
            stress_levels="EXTREME",
            exercise_hours="ZERO",
            life_happened=[],
            feeling_today="MEHHH",
            hours_of_sleep=5,
            sleep_quality="BAD",
            something_special=[],
        )
        daily_questionnaire_2.created_at = self.today + datetime.timedelta(days=2)
        daily_questionnaire_2.save()

        predictions = Prediction.objects.filter(user=self.user)
        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0].prediction_type, "ROUTINE_DONE")
        self.assertEqual(predictions[0].date, self.next_day.date())
        self.assertEqual(predictions[1].prediction_type, "DAILY_QUESTIONNAIRE_SKIPPED")
        self.assertEqual(predictions[1].date, self.today.date())

    @parameterized.expand(
        [
            ["2022-6-3", "2022-6-1", "2022-6-2", "MENSTRUATION_DURING"],
            ["2022-6-9", "2022-6-7", "2022-6-8", "MENSTRUATION_FOLLICULAR"],
            ["2022-6-14", "2022-6-12", "2022-6-13", "MENSTRUATION_OVULATION"],
            ["2022-6-20", "2022-6-18", "2022-6-19", "MENSTRUATION_LUTEAL"],
        ]
    )
    def test_menstruation_prediction(self, current_date, date1, date2, expected_prediction):
        with freeze_time(current_date):
            self.user_questionnaire.created_at = timezone.now() - datetime.timedelta(days=8)
            self.user_questionnaire.save()
            make(
                HealthCareEvent,
                user=self.user,
                event_type=HealthCareEventTypes.MENSTRUATION,
                duration=5,
                start_date="2022-6-3",
            )
            daily_questionnaire = make(
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
            prediction = Prediction.objects.filter(user=self.user).first()
            self.assertEqual(prediction.user, daily_questionnaire.user)
            self.assertEqual(prediction.date, daily_questionnaire.created_at.date())
            self.assertEqual(prediction.prediction_type, expected_prediction)

    def test_menstruation_prediction_or_other_type_predictions_do_not_repeat(self):
        make(
            HealthCareEvent,
            user=self.user,
            event_type=HealthCareEventTypes.MENSTRUATION,
            duration=5,
        )
        daily_questionnaires = make(
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
            _quantity=7,
        )

        for questionnaire in daily_questionnaires:
            questionnaire.created_at = self.today + datetime.timedelta(days=daily_questionnaires.index(questionnaire))
            questionnaire.save()

        predictions = Prediction.objects.filter(user=self.user)

        other_prediction_types = set(
            PredictionCategories.SKIN_TODAY_TYPES
            + PredictionCategories.SKIN_FEELING_TYPES
            + PredictionCategories.SLEEP_HOURS_TYPES
            + PredictionCategories.SLEEP_QUALITY_TYPES
            + PredictionCategories.EXERCISE_HOURS_TYPES
            + PredictionCategories.STRESS_TYPES
            + PredictionCategories.DIET_TYPES
            + PredictionCategories.WATER_INTAKE_TYPES
            + PredictionCategories.LIFE_HAPPENED_TYPES
        )

        self.assertEqual(
            predictions[0].prediction_type,
            PredictionTypes.MENSTRUATION_FOLLICULAR.value,
        )
        self.assertIn(predictions[1].prediction_type, other_prediction_types)
        self.assertIn(predictions[2].prediction_type, other_prediction_types)
        self.assertIn(predictions[3].prediction_type, other_prediction_types)
        self.assertIn(predictions[4].prediction_type, other_prediction_types)
        self.assertIn(predictions[5].prediction_type, other_prediction_types)
        self.assertEqual(predictions[6].prediction_type, PredictionTypes.MENSTRUATION_DURING.value)

        self.assertNotIn(predictions[0].prediction_type, [predictions[1], predictions[2]])
        self.assertNotIn(predictions[1].prediction_type, [predictions[2], predictions[3]])
        self.assertNotIn(predictions[2].prediction_type, [predictions[3], predictions[4]])
        self.assertNotIn(predictions[3].prediction_type, [predictions[4], predictions[5]])
        self.assertNotIn(predictions[4].prediction_type, [predictions[5], predictions[6]])

    @patch("apps.routines.signals.random.choice")
    def test_diet_prediction_balanced(self, random_choice):
        random_choice.return_value = "DIET_BALANCED"
        questionnaires = make(
            DailyQuestionnaire,
            user=self.user,
            diet_today="BALANCED",
            water=3,
            hours_of_sleep=6,
            _quantity=3,
        )
        for date, question in zip(self.dates, questionnaires):
            question.created_at = datetime.datetime.combine(date, datetime.datetime.min.time(), datetime.timezone.utc)
            question.save()
            questionnaires.append(question)
        prediction = Prediction.objects.filter(user=self.user).first()
        self.assertEqual(prediction.prediction_type, "DIET_BALANCED")

    @patch("apps.routines.signals.random.choice")
    def test_exercise_hours_prediction(self, random_choice):
        random_choice.return_value = "EXERCISE_HOURS_BAD"
        questionnaires = make(
            DailyQuestionnaire,
            user=self.user,
            exercise_hours="ZERO",
            water=3,
            hours_of_sleep=6,
            _quantity=3,
        )
        for date, question in zip(self.dates, questionnaires):
            question.created_at = datetime.datetime.combine(date, datetime.datetime.min.time(), datetime.timezone.utc)
            question.save()
            questionnaires.append(question)
        prediction = Prediction.objects.filter(user=self.user).first()
        self.assertEqual(prediction.prediction_type, "EXERCISE_HOURS_BAD")

    @patch("apps.routines.signals.random.choice")
    def test_life_happened_prediction(self, random_choice):
        random_choice.return_value = "LIFE_HAPPENED_COFFEE_OR_ALCOHOL_OR_JUNK_FOOD"
        questionnaires = make(
            DailyQuestionnaire,
            user=self.user,
            life_happened=["COFFEE"],
            water=2,
            hours_of_sleep=6,
            _quantity=3,
        )
        for date, question in zip(self.dates, questionnaires):
            question.created_at = datetime.datetime.combine(date, datetime.datetime.min.time(), datetime.timezone.utc)
            question.save()
            questionnaires.append(question)
        prediction = Prediction.objects.filter(user=self.user).first()
        self.assertEqual(prediction.prediction_type, "LIFE_HAPPENED_COFFEE_OR_ALCOHOL_OR_JUNK_FOOD")

    @patch("apps.routines.signals.random.choice")
    def test_skin_feel_prediction(self, random_choice):
        random_choice.return_value = "SKIN_FEELING_SENSITIVE"
        questionnaires = make(
            DailyQuestionnaire,
            user=self.user,
            skin_feel="SENSITIVE",
            water=3,
            hours_of_sleep=6,
            _quantity=3,
        )
        for date, question in zip(self.dates, questionnaires):
            question.created_at = datetime.datetime.combine(date, datetime.datetime.min.time(), datetime.timezone.utc)
            question.save()
            questionnaires.append(question)
        prediction = Prediction.objects.filter(user=self.user).first()
        self.assertEqual(prediction.prediction_type, "SKIN_FEELING_SENSITIVE")

    @patch("apps.routines.signals.random.choice")
    def test_skin_today_prediction(self, random_choice):
        random_choice.return_value = "SKIN_TODAY_WELL"
        questionnaires = make(
            DailyQuestionnaire,
            user=self.user,
            feeling_today="WELL",
            water=3,
            hours_of_sleep=6,
            _quantity=3,
        )
        for date, question in zip(self.dates, questionnaires):
            question.created_at = datetime.datetime.combine(date, datetime.datetime.min.time(), datetime.timezone.utc)
            question.save()
            questionnaires.append(question)
        prediction = Prediction.objects.filter(user=self.user).first()
        self.assertEqual(prediction.prediction_type, "SKIN_TODAY_WELL")

    @patch("apps.routines.signals.random.choice")
    def test_sleep_hours_prediction(self, random_choice):
        random_choice.return_value = "SLEEP_HOURS_GREATER_EQUAL_SEVEN"
        questionnaires = make(DailyQuestionnaire, user=self.user, water=3, hours_of_sleep=8, _quantity=3)
        for date, question in zip(self.dates, questionnaires):
            question.created_at = datetime.datetime.combine(date, datetime.datetime.min.time(), datetime.timezone.utc)
            question.save()
            questionnaires.append(question)
        prediction = Prediction.objects.filter(user=self.user).first()
        self.assertEqual(prediction.prediction_type, "SLEEP_HOURS_GREATER_EQUAL_SEVEN")

    @patch("apps.routines.signals.random.choice")
    def test_sleep_quality_prediction(self, random_choice):
        random_choice.return_value = "SLEEP_QUALITY_WELL_OR_LOVE_IT"
        questionnaires = make(
            DailyQuestionnaire,
            user=self.user,
            sleep_quality=SleepQuality.WELL,
            water=3,
            hours_of_sleep=6,
            _quantity=3,
        )
        for date, question in zip(self.dates, questionnaires):
            question.created_at = datetime.datetime.combine(date, datetime.datetime.min.time(), datetime.timezone.utc)
            question.save()
            questionnaires.append(question)
        prediction = Prediction.objects.filter(user=self.user).first()
        self.assertEqual(prediction.prediction_type, "SLEEP_QUALITY_WELL_OR_LOVE_IT")

    @patch("apps.routines.signals.random.choice")
    def test_sleep_quality_prediction_with_different_sleep_quality_values(self, random_choice):
        random_choice.return_value = "SLEEP_QUALITY_WELL_OR_LOVE_IT"
        make(
            DailyQuestionnaire,
            user=self.user,
            sleep_quality=SleepQuality.MEHHH,
            water=3,
            hours_of_sleep=6,
        )
        make(
            DailyQuestionnaire,
            user=self.user,
            sleep_quality=SleepQuality.BAD,
            water=3,
            hours_of_sleep=6,
        )
        make(
            DailyQuestionnaire,
            user=self.user,
            sleep_quality=SleepQuality.LOVE_IT,
            water=3,
            hours_of_sleep=6,
        )
        make(
            DailyQuestionnaire,
            user=self.user,
            sleep_quality=SleepQuality.WELL,
            water=3,
            hours_of_sleep=6,
        )
        daily_questionnaire_5 = make(
            DailyQuestionnaire,
            user=self.user,
            sleep_quality=SleepQuality.LOVE_IT,
            water=3,
            hours_of_sleep=6,
        )
        daily_questionnaire_5.created_at = self.next_day
        daily_questionnaire_5.save()
        prediction = Prediction.objects.filter(user=self.user).first()
        self.assertEqual(prediction.prediction_type, "SLEEP_QUALITY_WELL_OR_LOVE_IT")

    @patch("apps.routines.signals.random.choice")
    def test_stress_prediction(self, random_choice):
        random_choice.return_value = "STRESS_RELAXED"
        questionnaires = make(
            DailyQuestionnaire,
            user=self.user,
            stress_levels="RELAXED",
            water=3,
            hours_of_sleep=6,
            _quantity=3,
        )
        for date, question in zip(self.dates, questionnaires):
            question.created_at = datetime.datetime.combine(date, datetime.datetime.min.time(), datetime.timezone.utc)
            question.save()
            questionnaires.append(question)
        prediction = Prediction.objects.filter(user=self.user).first()
        self.assertEqual(prediction.prediction_type, "STRESS_RELAXED")

    @patch("apps.routines.signals.random.choice")
    def test_water_intake_prediction(self, random_choice):
        random_choice.return_value = "WATER_INTAKE_TWO_OR_THREE"
        questionnaires = make(DailyQuestionnaire, user=self.user, water=3, hours_of_sleep=6, _quantity=3)
        for date, question in zip(self.dates, questionnaires):
            question.created_at = datetime.datetime.combine(date, datetime.datetime.min.time(), datetime.timezone.utc)
            question.save()
            questionnaires.append(question)
        prediction = Prediction.objects.filter(user=self.user).first()
        self.assertEqual(prediction.prediction_type, "WATER_INTAKE_TWO_OR_THREE")

    def test_two_consecutive_daily_questionnaire_and_routine_predictions(self):
        for day in range(7):
            date = self.today - datetime.timedelta(days=day)
            am_routine = make(Routine, user=self.user, routine_type="AM")
            am_routine.created_at = date
            am_routine.save()
            pm_routine = make(Routine, user=self.user, routine_type="PM")
            pm_routine.created_at = date
            pm_routine.save()

        daily_questionnaires = make(
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
            _quantity=2,
        )
        daily_questionnaires[1].created_at = self.today + datetime.timedelta(days=1)
        daily_questionnaires[1].save()
        am_routine = make(Routine, user=self.user, routine_type="AM")
        am_routine.created_at = self.today + datetime.timedelta(days=1)
        am_routine.save()
        pm_routine = make(Routine, user=self.user, routine_type="PM")
        pm_routine.created_at = self.today + datetime.timedelta(days=1)
        pm_routine.save()

        predictions = Prediction.objects.filter(user=self.user)
        prediction_1 = predictions.last()
        prediction_2 = predictions.first()
        self.assertEqual(prediction_1.user, daily_questionnaires[0].user)
        self.assertEqual(prediction_1.date, daily_questionnaires[0].created_at.date())
        self.assertEqual(prediction_1.prediction_type, "DAILY_QUESTIONNAIRE_SKIPPED")
        self.assertEqual(prediction_2.user, daily_questionnaires[1].user)
        self.assertEqual(prediction_2.date, daily_questionnaires[1].created_at.date())
        self.assertEqual(prediction_2.prediction_type, "ROUTINE_DONE")

    def test_prediction_list_without_template(self):
        prediction = make(Prediction, user=self.user, date=self.dates[1])
        url = reverse("predictions-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        predictions = response.json()["results"]
        self.assertEqual(len(predictions), 1)
        self.assertEqual(predictions[0]["id"], prediction.id)
        self.assertEqual(predictions[0]["date"], prediction.date.strftime("%Y-%m-%d"))
        self.assertEqual(predictions[0]["prediction"], prediction.prediction_type)
        self.assertEqual(
            predictions[0]["created_at"],
            prediction.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertIsNone(predictions[0]["image"])
        self.assertIsNone(predictions[0]["title"])

    def test_prediction_list_with_translation(self):
        prediction_type = "WATER_INTAKE_TWO_OR_THREE"
        prediction_template = make(PredictionTemplate, name=prediction_type)
        translation = make(PredictionTemplateTranslation, template=prediction_template)
        prediction = make(
            Prediction,
            user=self.user,
            date=self.dates[1],
            prediction_type=prediction_type,
        )
        translation.image = self.get_image_file()
        translation.save()
        url = reverse("predictions-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        predictions = response.json()["results"]
        self.assertEqual(len(predictions), 1)
        self.assertEqual(predictions[0]["id"], prediction.id)
        self.assertEqual(predictions[0]["date"], prediction.date.strftime("%Y-%m-%d"))
        self.assertEqual(predictions[0]["prediction"], translation.body)
        self.assertIsNotNone(predictions[0]["image"])
        self.assertEqual(predictions[0]["image"], translation.image.url)
        self.assertEqual(predictions[0]["title"], translation.title)
        self.assertEqual(
            predictions[0]["created_at"],
            prediction.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
