import datetime
from random import uniform

from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from freezegun import freeze_time
from model_bakery.baker import make
from parameterized import parameterized
from rest_framework import status

from apps.home.models import PredictionTemplate, PredictionTemplateTranslation
from apps.questionnaire.models import UserQuestionnaire
from apps.routines import (
    SkinFeel,
    FeelingToday,
    DietBalance,
    LifeHappened,
    StressLevel,
    ExerciseHours,
    SleepQuality,
    TagCategories,
    RoutineType,
    SkinTrendCategories,
    PredictionTypes,
)
from apps.routines.models import (
    DailyQuestionnaire,
    UserTag,
    Routine,
    FaceScanAnalytics,
    FaceScan,
)
from apps.routines.progresses import get_skin_grade, is_recommendation_unlocked
from apps.utils.error_codes import Errors
from apps.utils.tests_utils import BaseTestCase


class ProgressTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.nutrition_tags = make(UserTag, category=TagCategories.NUTRITION, _quantity=2)
        self.skin_care_tags = make(UserTag, category=TagCategories.SKIN_CARE, _quantity=2)
        self.well_being_tags = make(UserTag, category=TagCategories.WELL_BEING, _quantity=2)
        prediction_template = make(PredictionTemplate, name=PredictionTypes.SKIN_FEELING_NORMAL)
        self.prediction_template_translation = make(PredictionTemplateTranslation, template=prediction_template)
        self.user_questionnaire = make(UserQuestionnaire, user=self.user)
        self.user_questionnaire.created_at = timezone.now() - datetime.timedelta(days=8)
        self.user_questionnaire.save()

    def test_skin_grade_calculation_with_random_float_value(self):
        value = uniform(0, 100)  # noqa S311
        grade = get_skin_grade(value)
        self.assertIsNotNone(grade)

    @parameterized.expand(
        [
            ["2022-06-29", False, False],
            ["2022-06-30", True, False],
            ["2022-06-30", True, True],
        ]
    )
    def test_monthly_progress_with_valid_data(  # noqa: CFQ001,C901
        self, query_date, recommendation_unlocked, has_previous_data
    ):
        self.query_limits["ANY GET REQUEST"] = 15
        with freeze_time(query_date):
            self._generate_monthly_data()
            if has_previous_data:
                self._generate_monthly_data("05")
            url = reverse("progress-monthly")
            response = self.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = response.json()
            self.assertEqual(results["total_days"], 30)
            self.assertEqual(results["total_daily_questionnaires"], 11)
            self.assertEqual(results["total_score"], 68.15)

            self.assertIsNotNone(results["message"])
            self.assertIn("days left till your full results", results["message"]["title"])
            self.assertEqual(
                results["message"]["subtitle"],
                "Keep tracking to get the most accurate result",
            )

            self.assertIsNotNone(results["routine"])
            if not has_previous_data:
                routines_data_current_month = results["routine"]["current_month"]
                routines_data_previous_month = results["routine"]["previous_month"]
                self.assertTrue(routines_data_current_month)
                self.assertFalse(routines_data_previous_month)
                routines_data = routines_data_current_month["data"]
                self.assertEqual(routines_data[0]["routine_type"], RoutineType.AM)
                self.assertEqual(routines_data[0]["count"], 11)
                self.assertEqual(routines_data[1]["routine_type"], RoutineType.PM)
                self.assertEqual(routines_data[1]["count"], 11)
                self.assertEqual(routines_data_current_month["avg_status"], "ROUTINE_MISSED")
                self.assertEqual(routines_data_current_month["progress"], 36.67)
            else:
                routines_data_current_month = results["routine"]["current_month"]
                routines_data_previous_month = results["routine"]["previous_month"]
                self.assertIsNotNone(routines_data_current_month)
                self.assertIsNotNone(routines_data_previous_month)
                self.assertEqual(results["routine"]["overall_progress"], 1.19)

                self.assertTrue(routines_data_current_month["data"])
                self.assertEqual(
                    routines_data_current_month["data"][0]["routine_type"],
                    RoutineType.AM,
                )
                self.assertEqual(routines_data_current_month["data"][0]["count"], 11)
                self.assertEqual(
                    routines_data_current_month["data"][1]["routine_type"],
                    RoutineType.PM,
                )
                self.assertEqual(routines_data_current_month["data"][1]["count"], 11)
                self.assertEqual(routines_data_current_month["avg_status"], "ROUTINE_MISSED")
                self.assertEqual(routines_data_current_month["progress"], 36.67)

                self.assertTrue(routines_data_previous_month["data"])
                self.assertEqual(
                    routines_data_previous_month["data"][0]["routine_type"],
                    RoutineType.AM,
                )
                self.assertEqual(routines_data_previous_month["data"][0]["count"], 11)
                self.assertEqual(
                    routines_data_previous_month["data"][1]["routine_type"],
                    RoutineType.PM,
                )
                self.assertEqual(routines_data_previous_month["data"][1]["count"], 11)
                self.assertEqual(routines_data_previous_month["avg_status"], "ROUTINE_MISSED")
                self.assertEqual(routines_data_previous_month["progress"], 35.48)

            self.assertIsNotNone(results["skin_feel"])
            skin_feel_data = results["skin_feel"]
            if not has_previous_data:
                skin_feel_data_current_month = skin_feel_data["current_month"]
                skin_feel_previous_month = skin_feel_data["previous_month"]
                self.assertIsNotNone(skin_feel_data_current_month)
                self.assertFalse(skin_feel_previous_month)
                self.assertIsNotNone(skin_feel_data_current_month["data"])
                self.assertEqual(len(skin_feel_data_current_month["data"]), 4)
                self.assertEqual(
                    skin_feel_data_current_month["data"][0]["answer"],
                    SkinFeel.NORMAL.value,
                )
                self.assertEqual(skin_feel_data_current_month["data"][0]["count"], 8)
                self.assertEqual(
                    skin_feel_data_current_month["data"][1]["answer"],
                    SkinFeel.SENSITIVE.value,
                )
                self.assertEqual(skin_feel_data_current_month["data"][1]["count"], 1)
                self.assertEqual(
                    skin_feel_data_current_month["data"][2]["answer"],
                    SkinFeel.DEHYDRATED.value,
                )
                self.assertEqual(skin_feel_data_current_month["data"][2]["count"], 1)
                self.assertEqual(
                    skin_feel_data_current_month["data"][3]["answer"],
                    SkinFeel.GREASY.value,
                )
                self.assertEqual(skin_feel_data_current_month["data"][3]["count"], 1)
                self.assertEqual(skin_feel_data_current_month["avg_answer"], SkinFeel.NORMAL.value)
                self.assertEqual(skin_feel_data_current_month["total_points"], 230)
                self.assertEqual(skin_feel_data_current_month["progress"], 83.64)
            else:
                skin_feel_data_current_month = skin_feel_data["current_month"]
                skin_feel_previous_month = skin_feel_data["previous_month"]
                self.assertIsNotNone(skin_feel_data_current_month)
                self.assertIsNotNone(skin_feel_previous_month)
                self.assertEqual(results["skin_feel"]["overall_progress"], 0)

                self.assertIsNotNone(skin_feel_data_current_month["data"])
                self.assertEqual(len(skin_feel_data_current_month["data"]), 4)
                self.assertEqual(
                    skin_feel_data_current_month["data"][0]["answer"],
                    SkinFeel.NORMAL.value,
                )
                self.assertEqual(skin_feel_data_current_month["data"][0]["count"], 8)
                self.assertEqual(
                    skin_feel_data_current_month["data"][1]["answer"],
                    SkinFeel.SENSITIVE.value,
                )
                self.assertEqual(skin_feel_data_current_month["data"][1]["count"], 1)
                self.assertEqual(
                    skin_feel_data_current_month["data"][2]["answer"],
                    SkinFeel.DEHYDRATED.value,
                )
                self.assertEqual(skin_feel_data_current_month["data"][2]["count"], 1)
                self.assertEqual(
                    skin_feel_data_current_month["data"][3]["answer"],
                    SkinFeel.GREASY.value,
                )
                self.assertEqual(skin_feel_data_current_month["data"][3]["count"], 1)
                self.assertEqual(skin_feel_data_current_month["avg_answer"], SkinFeel.NORMAL.value)
                self.assertEqual(skin_feel_data_current_month["total_points"], 230)
                self.assertEqual(skin_feel_data_current_month["progress"], 83.64)

                self.assertIsNotNone(skin_feel_previous_month["data"])
                self.assertEqual(len(skin_feel_previous_month["data"]), 4)
                self.assertEqual(
                    skin_feel_data_current_month["data"][0]["answer"],
                    SkinFeel.NORMAL.value,
                )
                self.assertEqual(skin_feel_data_current_month["data"][0]["count"], 8)
                self.assertEqual(
                    skin_feel_data_current_month["data"][1]["answer"],
                    SkinFeel.SENSITIVE.value,
                )
                self.assertEqual(skin_feel_data_current_month["data"][1]["count"], 1)
                self.assertEqual(
                    skin_feel_data_current_month["data"][2]["answer"],
                    SkinFeel.DEHYDRATED.value,
                )
                self.assertEqual(skin_feel_data_current_month["data"][2]["count"], 1)
                self.assertEqual(
                    skin_feel_data_current_month["data"][3]["answer"],
                    SkinFeel.GREASY.value,
                )
                self.assertEqual(skin_feel_data_current_month["data"][3]["count"], 1)
                self.assertEqual(skin_feel_previous_month["avg_answer"], SkinFeel.NORMAL.value)
                self.assertEqual(skin_feel_previous_month["total_points"], 230)
                self.assertEqual(skin_feel_previous_month["progress"], 83.64)

            self.assertIsNotNone(results["feeling_today"])
            feeling_today_data = results["feeling_today"]
            if not has_previous_data:
                feeling_today_data_current_month = feeling_today_data["current_month"]
                feeling_today_data_previous_month = feeling_today_data["previous_month"]
                self.assertIsNotNone(feeling_today_data_current_month)
                self.assertFalse(feeling_today_data_previous_month)
                self.assertIsNotNone(feeling_today_data_current_month["data"])
                self.assertEqual(len(feeling_today_data_current_month["data"]), 4)

                self.assertEqual(
                    feeling_today_data_current_month["data"][0]["answer"],
                    FeelingToday.LOVE_IT.value,
                )
                self.assertEqual(feeling_today_data_current_month["data"][0]["count"], 1)
                self.assertEqual(
                    feeling_today_data_current_month["data"][1]["answer"],
                    FeelingToday.WELL.value,
                )
                self.assertEqual(feeling_today_data_current_month["data"][1]["count"], 7)
                self.assertEqual(
                    feeling_today_data_current_month["data"][2]["answer"],
                    FeelingToday.MEHHH.value,
                )
                self.assertEqual(feeling_today_data_current_month["data"][2]["count"], 1)
                self.assertEqual(
                    feeling_today_data_current_month["data"][3]["answer"],
                    FeelingToday.BAD.value,
                )
                self.assertEqual(feeling_today_data_current_month["data"][3]["count"], 2)
                self.assertEqual(
                    feeling_today_data_current_month["avg_answer"],
                    FeelingToday.WELL.value,
                )
                self.assertEqual(feeling_today_data_current_month["total_points"], 185)
                self.assertEqual(feeling_today_data_current_month["progress"], 67.27)
            else:
                feeling_today_data_current_month = feeling_today_data["current_month"]
                feeling_today_data_previous_month = feeling_today_data["previous_month"]
                self.assertIsNotNone(feeling_today_data_current_month)
                self.assertIsNotNone(feeling_today_data_previous_month)
                self.assertEqual(results["feeling_today"]["overall_progress"], 0)

                self.assertIsNotNone(feeling_today_data_current_month["data"])
                self.assertEqual(len(feeling_today_data_current_month["data"]), 4)
                self.assertEqual(
                    feeling_today_data_current_month["data"][0]["answer"],
                    FeelingToday.LOVE_IT.value,
                )
                self.assertEqual(feeling_today_data_current_month["data"][0]["count"], 1)
                self.assertEqual(
                    feeling_today_data_current_month["data"][1]["answer"],
                    FeelingToday.WELL.value,
                )
                self.assertEqual(feeling_today_data_current_month["data"][1]["count"], 7)
                self.assertEqual(
                    feeling_today_data_current_month["data"][2]["answer"],
                    FeelingToday.MEHHH.value,
                )
                self.assertEqual(feeling_today_data_current_month["data"][2]["count"], 1)
                self.assertEqual(
                    feeling_today_data_current_month["data"][3]["answer"],
                    FeelingToday.BAD.value,
                )
                self.assertEqual(feeling_today_data_current_month["data"][3]["count"], 2)
                self.assertEqual(
                    feeling_today_data_current_month["avg_answer"],
                    FeelingToday.WELL.value,
                )
                self.assertEqual(feeling_today_data_current_month["total_points"], 185)
                self.assertEqual(feeling_today_data_current_month["progress"], 67.27)

                self.assertIsNotNone(feeling_today_data_previous_month["data"])
                self.assertEqual(len(feeling_today_data_previous_month["data"]), 4)
                self.assertEqual(
                    feeling_today_data_current_month["data"][0]["answer"],
                    FeelingToday.LOVE_IT.value,
                )
                self.assertEqual(feeling_today_data_current_month["data"][0]["count"], 1)
                self.assertEqual(
                    feeling_today_data_current_month["data"][1]["answer"],
                    FeelingToday.WELL.value,
                )
                self.assertEqual(feeling_today_data_current_month["data"][1]["count"], 7)
                self.assertEqual(
                    feeling_today_data_current_month["data"][2]["answer"],
                    FeelingToday.MEHHH.value,
                )
                self.assertEqual(feeling_today_data_current_month["data"][2]["count"], 1)
                self.assertEqual(
                    feeling_today_data_current_month["data"][3]["answer"],
                    FeelingToday.BAD.value,
                )
                self.assertEqual(feeling_today_data_current_month["data"][3]["count"], 2)
                self.assertEqual(
                    feeling_today_data_previous_month["avg_answer"],
                    FeelingToday.WELL.value,
                )
                self.assertEqual(feeling_today_data_previous_month["total_points"], 185)
                self.assertEqual(feeling_today_data_previous_month["progress"], 67.27)

            self.assertIsNotNone(results["life_happened"])
            life_happened_data = results["life_happened"]
            self.assertIsNotNone(life_happened_data["data"])
            self.assertEqual(len(life_happened_data["data"]), 4)
            self.assertEqual(
                life_happened_data["data"][0]["answer"],
                LifeHappened.JUNK_FOOD_AND_SWEETS.value,
            )
            self.assertEqual(life_happened_data["data"][0]["count"], 3)
            self.assertEqual(life_happened_data["data"][1]["answer"], LifeHappened.COFFEE.value)
            self.assertEqual(life_happened_data["data"][1]["count"], 2)
            self.assertEqual(life_happened_data["data"][2]["answer"], LifeHappened.INNOCENT.value)
            self.assertEqual(life_happened_data["data"][2]["count"], 8)
            self.assertEqual(life_happened_data["data"][3]["answer"], LifeHappened.ALCOHOL.value)
            self.assertEqual(life_happened_data["data"][3]["count"], 1)
            self.assertEqual(life_happened_data["avg_answer"], LifeHappened.INNOCENT.value)
            self.assertEqual(life_happened_data["total_points"], 240)
            self.assertEqual(life_happened_data["progress"], 68.57)
            if has_previous_data:
                self.assertEqual(life_happened_data["overall_progress"], 68.57)

            self.assertIsNotNone(results["stress_levels"])
            stress_level_data = results["stress_levels"]
            self.assertIsNotNone(stress_level_data["data"])
            self.assertEqual(len(stress_level_data["data"]), 3)
            self.assertEqual(stress_level_data["data"][0]["answer"], StressLevel.RELAXED.value)
            self.assertEqual(stress_level_data["data"][0]["count"], 8)
            self.assertEqual(stress_level_data["data"][1]["answer"], StressLevel.MODERATE.value)
            self.assertEqual(stress_level_data["data"][1]["count"], 2)
            self.assertEqual(stress_level_data["data"][2]["answer"], StressLevel.EXTREME.value)
            self.assertEqual(stress_level_data["data"][2]["count"], 1)
            self.assertEqual(stress_level_data["avg_answer"], StressLevel.RELAXED.value)
            self.assertEqual(stress_level_data["total_points"], 235)
            self.assertEqual(stress_level_data["progress"], 85.45)
            if has_previous_data:
                self.assertEqual(stress_level_data["overall_progress"], 0)

            self.assertIsNotNone(results["water"])
            water_intake_data = results["water"]
            self.assertIsNotNone(water_intake_data["data"])
            self.assertEqual(len(water_intake_data["data"]), 4)
            self.assertEqual(water_intake_data["data"][0]["answer"], 3)
            self.assertEqual(water_intake_data["data"][0]["count"], 7)
            self.assertEqual(water_intake_data["data"][1]["answer"], 2)
            self.assertEqual(water_intake_data["data"][1]["count"], 2)
            self.assertEqual(water_intake_data["data"][2]["answer"], 1)
            self.assertEqual(water_intake_data["data"][2]["count"], 1)
            self.assertEqual(water_intake_data["data"][3]["answer"], 0)
            self.assertEqual(water_intake_data["data"][3]["count"], 1)
            self.assertEqual(water_intake_data["avg_answer"], 3)
            self.assertEqual(water_intake_data["total_points"], 225)
            self.assertEqual(water_intake_data["progress"], 81.82)
            if has_previous_data:
                self.assertEqual(water_intake_data["overall_progress"], 0)

            self.assertIsNotNone(results["exercise_hours"])
            exercise_hours_data = results["exercise_hours"]
            self.assertIsNotNone(exercise_hours_data["data"])
            self.assertEqual(len(exercise_hours_data["data"]), 6)
            self.assertEqual(exercise_hours_data["data"][0]["answer"], ExerciseHours.TWO_PLUS.value)
            self.assertEqual(exercise_hours_data["data"][0]["count"], 6)
            self.assertEqual(exercise_hours_data["data"][1]["answer"], ExerciseHours.TWO_HOURS.value)
            self.assertEqual(exercise_hours_data["data"][1]["count"], 1)
            self.assertEqual(
                exercise_hours_data["data"][2]["answer"],
                ExerciseHours.FORTY_FIVE_MIN.value,
            )
            self.assertEqual(exercise_hours_data["data"][2]["count"], 1)
            self.assertEqual(exercise_hours_data["data"][3]["answer"], ExerciseHours.THIRTY_MIN.value)
            self.assertEqual(exercise_hours_data["data"][3]["count"], 1)
            self.assertEqual(exercise_hours_data["data"][4]["answer"], ExerciseHours.TWENTY_MIN.value)
            self.assertEqual(exercise_hours_data["data"][4]["count"], 1)
            self.assertEqual(exercise_hours_data["data"][5]["answer"], ExerciseHours.ZERO.value)
            self.assertEqual(exercise_hours_data["data"][5]["count"], 1)
            self.assertEqual(exercise_hours_data["avg_answer"], ExerciseHours.TWO_PLUS.value)
            self.assertEqual(exercise_hours_data["total_points"], 225)
            self.assertEqual(exercise_hours_data["progress"], 81.82)
            if has_previous_data:
                self.assertEqual(exercise_hours_data["overall_progress"], 0)

            self.assertIsNotNone(results["sleep"])
            self.assertEqual(results["sleep"]["progress"], 73.63)
            if has_previous_data:
                self.assertEqual(results["sleep"]["overall_progress"], 0)
            sleep_quality_data = results["sleep"]["sleep_quality"]
            self.assertIsNotNone(sleep_quality_data["data"])
            self.assertEqual(len(sleep_quality_data["data"]), 4)
            self.assertEqual(sleep_quality_data["data"][0]["answer"], SleepQuality.LOVE_IT.value)
            self.assertEqual(sleep_quality_data["data"][0]["count"], 7)
            self.assertEqual(sleep_quality_data["data"][1]["answer"], SleepQuality.WELL.value)
            self.assertEqual(sleep_quality_data["data"][1]["count"], 1)
            self.assertEqual(sleep_quality_data["data"][2]["answer"], SleepQuality.MEHHH.value)
            self.assertEqual(sleep_quality_data["data"][2]["count"], 2)
            self.assertEqual(sleep_quality_data["data"][3]["answer"], SleepQuality.BAD.value)
            self.assertEqual(sleep_quality_data["data"][3]["count"], 1)
            self.assertEqual(sleep_quality_data["avg_answer"], SleepQuality.LOVE_IT.value)
            self.assertEqual(sleep_quality_data["total_points"], 220)
            self.assertEqual(sleep_quality_data["progress"], 80)

            sleep_hours_data = results["sleep"]["hours_of_sleep"]
            self.assertIsNotNone(sleep_hours_data["data"])
            self.assertEqual(len(sleep_hours_data["data"]), 5)
            self.assertEqual(sleep_hours_data["data"][0]["answer"], 8)
            self.assertEqual(sleep_hours_data["data"][0]["count"], 6)
            self.assertEqual(sleep_hours_data["data"][1]["answer"], 7)
            self.assertEqual(sleep_hours_data["data"][1]["count"], 1)
            self.assertEqual(sleep_hours_data["data"][2]["answer"], 6)
            self.assertEqual(sleep_hours_data["data"][2]["count"], 1)
            self.assertEqual(sleep_hours_data["data"][3]["answer"], 4)
            self.assertEqual(sleep_hours_data["data"][3]["count"], 2)
            self.assertEqual(sleep_hours_data["data"][4]["answer"], 3)
            self.assertEqual(sleep_hours_data["data"][4]["count"], 1)
            self.assertEqual(sleep_hours_data["avg_answer"], 8)
            self.assertEqual(sleep_hours_data["total_points"], 185)
            self.assertEqual(sleep_hours_data["progress"], 67.27)

            self.assertIsNotNone(results["diet_today"])
            diet_today_data = results["diet_today"]
            self.assertIsNotNone(life_happened_data["data"])
            self.assertEqual(len(diet_today_data["data"]), 3)
            self.assertEqual(diet_today_data["data"][0]["answer"], DietBalance.BALANCED.value)
            self.assertEqual(diet_today_data["data"][0]["count"], 8)
            self.assertEqual(diet_today_data["data"][1]["answer"], DietBalance.MILDLY_BALANCED.value)
            self.assertEqual(diet_today_data["data"][1]["count"], 2)
            self.assertEqual(diet_today_data["data"][2]["answer"], DietBalance.UNBALANCED.value)
            self.assertEqual(diet_today_data["data"][2]["count"], 1)
            self.assertEqual(diet_today_data["avg_answer"], DietBalance.BALANCED.value)
            self.assertEqual(diet_today_data["total_points"], 435)
            self.assertEqual(diet_today_data["progress"], 79.09)
            if has_previous_data:
                self.assertEqual(diet_today_data["overall_progress"], 0)

            self.assertIsNotNone(results["tags"])
            self.assertEqual(len(results["tags"]), 3)
            self.assertIsNotNone(results["tags"][0])
            skin_care_data = results["tags"][0]
            self.assertEqual(skin_care_data["category"], "skin_care_tags")
            self.assertTrue(skin_care_data["data"])
            self.assertEqual(skin_care_data["data"][0]["answer"], self.skin_care_tags[1].name)
            self.assertEqual(skin_care_data["data"][0]["count"], 9)
            self.assertEqual(skin_care_data["data"][1]["answer"], self.skin_care_tags[0].name)
            self.assertEqual(skin_care_data["data"][1]["count"], 9)

            self.assertIsNotNone(results["tags"][1])
            well_being_data = results["tags"][1]
            self.assertEqual(well_being_data["category"], "well_being_tags")
            self.assertTrue(well_being_data["data"])
            self.assertEqual(well_being_data["data"][0]["answer"], self.well_being_tags[1].name)
            self.assertEqual(well_being_data["data"][0]["count"], 10)
            self.assertEqual(well_being_data["data"][1]["answer"], self.well_being_tags[0].name)
            self.assertEqual(well_being_data["data"][1]["count"], 7)

            self.assertIsNotNone(results["tags"][2])
            nutrition_data = results["tags"][2]
            self.assertEqual(nutrition_data["category"], "nutrition_tags")
            self.assertTrue(nutrition_data["data"])
            self.assertEqual(nutrition_data["data"][0]["answer"], self.nutrition_tags[1].name)
            self.assertEqual(nutrition_data["data"][0]["count"], 9)

            self.assertTrue(results["skin_trend"])
            face_analytics = FaceScanAnalytics.objects.filter(
                face_scan__user=self.user, created_at__date__month__gte=6
            ).order_by("created_at__date")
            self.assertEqual(results["total_face_scans"], 11)
            self.assertEqual(results["total_face_scans"], face_analytics.count())
            self.assertIsNotNone(results["skin_trend"]["skin_score"])
            skin_score_data = results["skin_trend"]["skin_score"]
            self.assertIsNotNone(skin_score_data["data"])
            self.assertEqual(len(skin_score_data["data"]), 3)
            self.assertEqual(skin_score_data["data"][0]["answer"], SkinTrendCategories.ADVANCED.value)
            self.assertEqual(skin_score_data["data"][0]["count"], 3)
            self.assertEqual(
                skin_score_data["data"][1]["answer"],
                SkinTrendCategories.INTERMEDIATE.value,
            )
            self.assertEqual(skin_score_data["data"][1]["count"], 8)
            self.assertEqual(skin_score_data["data"][2]["answer"], SkinTrendCategories.BEGINNER.value)
            self.assertEqual(skin_score_data["data"][2]["count"], 0)
            self.assertEqual(skin_score_data["avg_level"], SkinTrendCategories.INTERMEDIATE.value)
            self.assertEqual(skin_score_data["progress"], 63.19)
            self.assertIsNotNone(results["skin_trend"]["other_score"])
            other_score_data = results["skin_trend"]["other_score"]
            self.assertEqual(
                results["skin_trend"]["other_score"]["avg_level"],
                SkinTrendCategories.INTERMEDIATE.value,
            )
            self.assertEqual(results["skin_trend"]["other_score"]["progress"], 63.19)
            self.assertEqual(
                other_score_data["data"]["acne"]["level"],
                SkinTrendCategories.INTERMEDIATE.value,
            )
            self.assertEqual(other_score_data["data"]["acne"]["value"], 60.2)
            self.assertEqual(
                other_score_data["data"]["hydration"]["level"],
                SkinTrendCategories.INTERMEDIATE.value,
            )
            self.assertEqual(other_score_data["data"]["hydration"]["value"], 51.0)
            self.assertEqual(
                other_score_data["data"]["pigmentation"]["level"],
                SkinTrendCategories.BEGINNER.value,
            )
            self.assertEqual(other_score_data["data"]["pigmentation"]["value"], 46.84)
            self.assertEqual(
                other_score_data["data"]["pores"]["level"],
                SkinTrendCategories.ADVANCED.value,
            )
            self.assertEqual(other_score_data["data"]["pores"]["value"], 82.05)
            self.assertEqual(
                other_score_data["data"]["redness"]["level"],
                SkinTrendCategories.INTERMEDIATE.value,
            )
            self.assertEqual(other_score_data["data"]["redness"]["value"], 72.19)
            self.assertEqual(
                other_score_data["data"]["uniformness"]["level"],
                SkinTrendCategories.INTERMEDIATE.value,
            )
            self.assertEqual(other_score_data["data"]["uniformness"]["value"], 66.84)
            if has_previous_data:
                self.assertEqual(results["skin_trend"]["overall_progress"], 0)

            if recommendation_unlocked:
                recommendation_data = results.get("recommendation")
                self.assertIsNotNone(recommendation_data)
                skin_feel_recommendation = recommendation_data.get("skin_feel")
                self.assertIsNotNone(skin_feel_recommendation)
                self.assertEqual(
                    skin_feel_recommendation["recommendation"],
                    self.prediction_template_translation.body,
                )
                self.assertIsNone(skin_feel_recommendation["image"])
                self.assertEqual(
                    skin_feel_recommendation["title"],
                    self.prediction_template_translation.title,
                )
                feeling_today_recommendation = recommendation_data.get("feeling_today")
                self.assertIsNotNone(feeling_today_recommendation)
                self.assertEqual(
                    feeling_today_recommendation["recommendation"],
                    PredictionTypes.SKIN_TODAY_WELL.value,
                )
                self.assertIsNone(feeling_today_recommendation["image"])
                self.assertIsNone(feeling_today_recommendation["title"])
                routine_recommendation = recommendation_data.get("routine")
                self.assertIsNotNone(routine_recommendation)
                self.assertEqual(
                    routine_recommendation["recommendation"],
                    PredictionTypes.ROUTINE_MISSED.value,
                )
                self.assertIsNone(routine_recommendation["image"])
                self.assertIsNone(routine_recommendation["title"])
            else:
                self.assertIsNone(results.get("recommendation"))

    def test_monthly_progress_with_no_data(self):  # noqa: CFQ001
        self.query_limits["ANY GET REQUEST"] = 7
        url = reverse("progress-monthly")
        query_params = {"month": "2022-06"}
        response = self.get(f"{url}?{urlencode(query_params)}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()
        self.assertEqual(results["total_days"], 30)
        self.assertEqual(results["total_daily_questionnaires"], 0)
        self.assertEqual(results["total_face_scans"], 0)
        self.assertIsNotNone(results["message"])
        self.assertEqual(results["message"]["title"], "You filled 0/30 questionnaires")
        self.assertEqual(results["message"]["subtitle"], "Enjoy your results")
        self.assertIsNotNone(results["routine"])
        self.assertDictEqual(
            results["routine"],
            {
                "current_month": {
                    "data": [],
                    "avg_status": "ROUTINE_SKIPPED",
                    "progress": 0.0,
                },
                "previous_month": None,
            },
        )
        self.assertIsNotNone(results["skin_feel"])
        self.assertDictEqual(
            results["skin_feel"],
            {
                "current_month": {
                    "data": [],
                    "total_points": 0,
                    "progress": 0.0,
                    "avg_answer": None,
                },
                "previous_month": None,
            },
        )
        self.assertIsNotNone(results["stress_levels"])
        self.assertFalse(results["stress_levels"]["data"])
        self.assertEqual(results["stress_levels"]["avg_answer"], None)
        self.assertEqual(results["stress_levels"]["progress"], 0)
        self.assertEqual(results["stress_levels"]["total_points"], 0)
        self.assertIsNotNone(results["sleep"])
        self.assertEqual(results["sleep"]["progress"], 0)
        self.assertIsNotNone(results["sleep"]["sleep_quality"])
        self.assertEqual(results["sleep"]["sleep_quality"]["avg_answer"], None)
        self.assertEqual(results["sleep"]["sleep_quality"]["progress"], 0)
        self.assertEqual(results["sleep"]["sleep_quality"]["total_points"], 0)
        self.assertFalse(results["sleep"]["sleep_quality"]["data"])
        self.assertIsNotNone(results["sleep"]["hours_of_sleep"])
        self.assertEqual(results["sleep"]["hours_of_sleep"]["avg_answer"], None)
        self.assertEqual(results["sleep"]["hours_of_sleep"]["progress"], 0)
        self.assertEqual(results["sleep"]["hours_of_sleep"]["total_points"], 0)
        self.assertFalse(results["sleep"]["hours_of_sleep"]["data"])
        self.assertIsNotNone(results["tags"])
        tags = results["tags"]
        self.assertEqual(len(tags), 3)
        self.assertEqual(tags[0]["category"], "skin_care_tags")
        self.assertFalse(tags[0]["data"])
        self.assertEqual(tags[1]["category"], "well_being_tags")
        self.assertFalse(tags[1]["data"])
        self.assertEqual(tags[2]["category"], "nutrition_tags")
        self.assertFalse(tags[2]["data"])
        self.assertIsNotNone(results["feeling_today"])
        self.assertDictEqual(
            results["feeling_today"],
            {
                "current_month": {
                    "data": [],
                    "total_points": 0,
                    "progress": 0.0,
                    "avg_answer": None,
                },
                "previous_month": None,
            },
        )
        self.assertIsNotNone(results["life_happened"])
        self.assertFalse(results["life_happened"]["data"])
        self.assertEqual(results["life_happened"]["avg_answer"], None)
        self.assertEqual(results["life_happened"]["progress"], 0)
        self.assertEqual(results["life_happened"]["total_points"], 0)
        self.assertIsNotNone(results["diet_today"])
        self.assertFalse(results["diet_today"]["data"])
        self.assertEqual(results["diet_today"]["avg_answer"], None)
        self.assertEqual(results["diet_today"]["progress"], 0)
        self.assertEqual(results["diet_today"]["total_points"], 0)
        self.assertIsNotNone(results["water"])
        self.assertFalse(results["water"]["data"])
        self.assertEqual(results["water"]["avg_answer"], None)
        self.assertEqual(results["water"]["progress"], 0)
        self.assertEqual(results["water"]["total_points"], 0)
        self.assertIsNotNone(results["exercise_hours"])
        self.assertEqual(results["exercise_hours"]["avg_answer"], None)
        self.assertFalse(results["exercise_hours"]["data"])
        self.assertEqual(results["exercise_hours"]["progress"], 0)
        self.assertEqual(results["exercise_hours"]["total_points"], 0)
        self.assertFalse(results["skin_trend"])
        self.assertFalse(results["recommendation"])
        self.assertEqual(results["total_score"], 0)

    @freeze_time("2022-06-01")
    def test_future_monthly_progress(self):
        self.query_limits["ANY GET REQUEST"] = 7
        url = reverse("progress-monthly")
        query_params = {"month": "2022-07"}
        response = self.get(f"{url}?{urlencode(query_params)}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), [Errors.FUTURE_MONTH_SELECTED_FOR_MONTHLY_PROGRESS.value])

    def _generate_monthly_data(self, month="06"):  # noqa: CFQ001
        months_data = {
            f"2022-{month}-01": {
                "questionnaires": {
                    "skin_feel": SkinFeel.SENSITIVE,
                    "feeling_today": FeelingToday.BAD,
                    "diet_today": DietBalance.MILDLY_BALANCED,
                    "water": 0,
                    "life_happened": [
                        LifeHappened.JUNK_FOOD_AND_SWEETS,
                        LifeHappened.COFFEE,
                    ],
                    "stress_levels": StressLevel.MODERATE,
                    "exercise_hours": ExerciseHours.ZERO,
                    "hours_of_sleep": 3,
                    "sleep_quality": SleepQuality.BAD,
                    "tags_for_skin_care": [
                        self.skin_care_tags[0].pk,
                        self.skin_care_tags[1].pk,
                    ],
                    "tags_for_well_being": [self.well_being_tags[1].pk],
                    "tags_for_nutrition": [self.nutrition_tags[1].pk],
                },
                "skin_analytics": {
                    "acne": 70,
                    "lines": 90,
                    "wrinkles": 70,
                    "pigmentation": 80,
                    "translucency": 90,
                    "pores": 90,
                    "uniformness": 85,
                    "hydration": 90,
                    "redness": 82,
                },
            },
            f"2022-{month}-02": {
                "questionnaires": {
                    "skin_feel": SkinFeel.NORMAL,
                    "feeling_today": FeelingToday.WELL,
                    "diet_today": DietBalance.BALANCED,
                    "water": 2,
                    "life_happened": [LifeHappened.INNOCENT],
                    "stress_levels": StressLevel.RELAXED,
                    "exercise_hours": ExerciseHours.FORTY_FIVE_MIN,
                    "hours_of_sleep": 7,
                    "sleep_quality": SleepQuality.LOVE_IT,
                    "tags_for_skin_care": [self.skin_care_tags[0].pk],
                    "tags_for_well_being": [self.well_being_tags[0].pk],
                    "tags_for_nutrition": [self.nutrition_tags[1].pk],
                },
                "skin_analytics": {
                    "acne": 78,
                    "lines": 88,
                    "wrinkles": 97,
                    "pigmentation": 58,
                    "translucency": 60,
                    "pores": 70,
                    "uniformness": 85,
                    "hydration": 40,
                    "redness": 72,
                },
            },
            f"2022-{month}-03": {
                "questionnaires": {
                    "skin_feel": SkinFeel.GREASY,
                    "feeling_today": FeelingToday.MEHHH,
                    "diet_today": DietBalance.MILDLY_BALANCED,
                    "water": 1,
                    "life_happened": [
                        LifeHappened.COFFEE,
                        LifeHappened.JUNK_FOOD_AND_SWEETS,
                    ],
                    "stress_levels": StressLevel.EXTREME,
                    "exercise_hours": ExerciseHours.TWENTY_MIN,
                    "hours_of_sleep": 4,
                    "sleep_quality": SleepQuality.MEHHH,
                    "tags_for_skin_care": [self.skin_care_tags[1].pk],
                    "tags_for_well_being": [self.well_being_tags[1].pk],
                    "tags_for_nutrition": [self.nutrition_tags[1].pk],
                },
                "skin_analytics": {
                    "acne": 90,
                    "lines": 80,
                    "wrinkles": 70,
                    "pigmentation": 70,
                    "translucency": 90,
                    "pores": 60,
                    "uniformness": 85,
                    "hydration": 90,
                    "redness": 92,
                },
            },
            f"2022-{month}-04": {
                "questionnaires": {
                    "skin_feel": SkinFeel.DEHYDRATED,
                    "feeling_today": FeelingToday.BAD,
                    "diet_today": DietBalance.UNBALANCED,
                    "water": 2,
                    "life_happened": [
                        LifeHappened.JUNK_FOOD_AND_SWEETS,
                        LifeHappened.ALCOHOL,
                    ],
                    "stress_levels": StressLevel.MODERATE,
                    "exercise_hours": ExerciseHours.THIRTY_MIN,
                    "hours_of_sleep": 4,
                    "sleep_quality": SleepQuality.MEHHH,
                    "tags_for_skin_care": [self.skin_care_tags[0].pk],
                    "tags_for_well_being": [self.well_being_tags[1].pk],
                    "tags_for_nutrition": [self.nutrition_tags[0].pk],
                },
                "skin_analytics": {
                    "acne": 50,
                    "lines": 30,
                    "wrinkles": 70,
                    "pigmentation": 30,
                    "translucency": 50,
                    "pores": 95,
                    "uniformness": 75,
                    "hydration": 69,
                    "redness": 88,
                },
            },
            f"2022-{month}-05": {
                "questionnaires": {
                    "skin_feel": SkinFeel.NORMAL,
                    "feeling_today": FeelingToday.LOVE_IT,
                    "diet_today": DietBalance.BALANCED,
                    "water": 3,
                    "life_happened": [LifeHappened.INNOCENT],
                    "stress_levels": StressLevel.RELAXED,
                    "exercise_hours": ExerciseHours.TWO_HOURS,
                    "hours_of_sleep": 6,
                    "sleep_quality": SleepQuality.WELL,
                    "tags_for_skin_care": [self.skin_care_tags[1].pk],
                    "tags_for_well_being": [self.well_being_tags[1].pk],
                    "tags_for_nutrition": [self.nutrition_tags[0].pk],
                },
                "skin_analytics": {
                    "acne": 0,
                    "lines": 50,
                    "wrinkles": 70,
                    "pigmentation": 90,
                    "translucency": 90,
                    "pores": 40,
                    "uniformness": 85,
                    "hydration": 75,
                    "redness": 22,
                },
            },
            f"2022-{month}-06": {
                "questionnaires": {
                    "skin_feel": SkinFeel.NORMAL,
                    "feeling_today": FeelingToday.WELL,
                    "diet_today": DietBalance.BALANCED,
                    "water": 3,
                    "life_happened": [LifeHappened.INNOCENT],
                    "stress_levels": StressLevel.RELAXED,
                    "exercise_hours": ExerciseHours.TWO_PLUS,
                    "hours_of_sleep": 8,
                    "sleep_quality": SleepQuality.LOVE_IT,
                    "tags_for_skin_care": [
                        self.skin_care_tags[0].pk,
                        self.skin_care_tags[1].pk,
                    ],
                    "tags_for_well_being": [
                        self.well_being_tags[0].pk,
                        self.well_being_tags[1].pk,
                    ],
                    "tags_for_nutrition": [self.nutrition_tags[1].pk],
                },
                "skin_analytics": {
                    "acne": 70,
                    "lines": 90,
                    "wrinkles": 70,
                    "pigmentation": 80,
                    "translucency": 90,
                    "pores": 90,
                    "uniformness": 85,
                    "hydration": 90,
                    "redness": 82,
                },
            },
            f"2022-{month}-07": {
                "questionnaires": {
                    "skin_feel": SkinFeel.NORMAL,
                    "feeling_today": FeelingToday.WELL,
                    "diet_today": DietBalance.BALANCED,
                    "water": 3,
                    "life_happened": [LifeHappened.INNOCENT],
                    "stress_levels": StressLevel.RELAXED,
                    "exercise_hours": ExerciseHours.TWO_PLUS,
                    "hours_of_sleep": 8,
                    "sleep_quality": SleepQuality.LOVE_IT,
                    "tags_for_skin_care": [
                        self.skin_care_tags[0].pk,
                        self.skin_care_tags[1].pk,
                    ],
                    "tags_for_well_being": [
                        self.well_being_tags[0].pk,
                        self.well_being_tags[1].pk,
                    ],
                    "tags_for_nutrition": [self.nutrition_tags[1].pk],
                },
                "skin_analytics": {
                    "acne": 95,
                    "lines": 80,
                    "wrinkles": 90,
                    "pigmentation": 60,
                    "translucency": 70,
                    "pores": 50,
                    "uniformness": 85,
                    "hydration": 90,
                    "redness": 82,
                },
            },
            f"2022-{month}-08": {
                "questionnaires": {
                    "skin_feel": SkinFeel.NORMAL,
                    "feeling_today": FeelingToday.WELL,
                    "diet_today": DietBalance.BALANCED,
                    "water": 3,
                    "life_happened": [LifeHappened.INNOCENT],
                    "stress_levels": StressLevel.RELAXED,
                    "exercise_hours": ExerciseHours.TWO_PLUS,
                    "hours_of_sleep": 8,
                    "sleep_quality": SleepQuality.LOVE_IT,
                    "tags_for_skin_care": [
                        self.skin_care_tags[0].pk,
                        self.skin_care_tags[1].pk,
                    ],
                    "tags_for_well_being": [
                        self.well_being_tags[0].pk,
                        self.well_being_tags[1].pk,
                    ],
                    "tags_for_nutrition": [self.nutrition_tags[1].pk],
                },
                "skin_analytics": {
                    "acne": 50,
                    "lines": 60,
                    "wrinkles": 40,
                    "pigmentation": 90,
                    "translucency": 79,
                    "pores": 70,
                    "uniformness": 55,
                    "hydration": 30,
                    "redness": 92,
                },
            },
            f"2022-{month}-09": {
                "questionnaires": {
                    "skin_feel": SkinFeel.NORMAL,
                    "feeling_today": FeelingToday.WELL,
                    "diet_today": DietBalance.BALANCED,
                    "water": 3,
                    "life_happened": [LifeHappened.INNOCENT],
                    "stress_levels": StressLevel.RELAXED,
                    "exercise_hours": ExerciseHours.TWO_PLUS,
                    "hours_of_sleep": 8,
                    "sleep_quality": SleepQuality.LOVE_IT,
                    "tags_for_skin_care": [
                        self.skin_care_tags[0].pk,
                        self.skin_care_tags[1].pk,
                    ],
                    "tags_for_well_being": [
                        self.well_being_tags[0].pk,
                        self.well_being_tags[1].pk,
                    ],
                    "tags_for_nutrition": [self.nutrition_tags[1].pk],
                },
                "skin_analytics": {
                    "acne": 40,
                    "lines": 70,
                    "wrinkles": 90,
                    "pigmentation": 40,
                    "translucency": 60,
                    "pores": 90,
                    "uniformness": 75,
                    "hydration": 90,
                    "redness": 62,
                },
            },
            f"2022-{month}-10": {
                "questionnaires": {
                    "skin_feel": SkinFeel.NORMAL,
                    "feeling_today": FeelingToday.WELL,
                    "diet_today": DietBalance.BALANCED,
                    "water": 3,
                    "life_happened": [LifeHappened.INNOCENT],
                    "stress_levels": StressLevel.RELAXED,
                    "exercise_hours": ExerciseHours.TWO_PLUS,
                    "hours_of_sleep": 8,
                    "sleep_quality": SleepQuality.LOVE_IT,
                    "tags_for_skin_care": [
                        self.skin_care_tags[0].pk,
                        self.skin_care_tags[1].pk,
                    ],
                    "tags_for_well_being": [
                        self.well_being_tags[0].pk,
                        self.well_being_tags[1].pk,
                    ],
                    "tags_for_nutrition": [self.nutrition_tags[1].pk],
                },
                "skin_analytics": {
                    "acne": 90,
                    "lines": 90,
                    "wrinkles": 40,
                    "pigmentation": 88,
                    "translucency": 70,
                    "pores": 90,
                    "uniformness": 85,
                    "hydration": 50,
                    "redness": 32,
                },
            },
            f"2022-{month}-20": {
                "questionnaires": {
                    "skin_feel": SkinFeel.NORMAL,
                    "feeling_today": FeelingToday.WELL,
                    "diet_today": DietBalance.BALANCED,
                    "water": 3,
                    "life_happened": [LifeHappened.INNOCENT],
                    "stress_levels": StressLevel.RELAXED,
                    "exercise_hours": ExerciseHours.TWO_PLUS,
                    "hours_of_sleep": 8,
                    "sleep_quality": SleepQuality.LOVE_IT,
                    "tags_for_skin_care": [
                        self.skin_care_tags[0].pk,
                        self.skin_care_tags[1].pk,
                    ],
                    "tags_for_well_being": [
                        self.well_being_tags[0].pk,
                        self.well_being_tags[1].pk,
                    ],
                    "tags_for_nutrition": [self.nutrition_tags[1].pk],
                },
                "skin_analytics": {
                    "acne": 50,
                    "lines": 40,
                    "wrinkles": 90,
                    "pigmentation": 20,
                    "translucency": 10,
                    "pores": 80,
                    "uniformness": 55,
                    "hydration": 40,
                    "redness": 92,
                },
            },
        }
        for date in months_data.keys():
            with freeze_time(date):
                skin_care_tags = months_data[date]["questionnaires"].pop("tags_for_skin_care")
                well_being_tags = months_data[date]["questionnaires"].pop("tags_for_well_being")
                nutrition_tags = months_data[date]["questionnaires"].pop("tags_for_nutrition")
                questionnaire = make(
                    DailyQuestionnaire,
                    user=self.user,
                    **months_data[date]["questionnaires"],
                )
                questionnaire.tags_for_skin_care.add(*skin_care_tags)
                questionnaire.tags_for_well_being.add(*well_being_tags)
                questionnaire.tags_for_nutrition.add(*nutrition_tags)
                make(Routine, user=self.user, routine_type=RoutineType.AM)
                make(Routine, user=self.user, routine_type=RoutineType.PM)
                face_scan = make(FaceScan, user=self.user)
                skin_analytics_data = months_data[date]["skin_analytics"]
                make(
                    FaceScanAnalytics,
                    face_scan=face_scan,
                    is_valid=True,
                    **skin_analytics_data,
                )


class IsRecommendationUnlockedTest(BaseTestCase):
    today = timezone.now().date()

    year_data = {today.year - 1: True, today.year: False, today.year + 1: False}
    dates_to_test = [
        [datetime.date(year=year, month=month, day=day), expected]
        for year, expected in year_data.items()
        for month in [1, 3]
        for day in [1, 31]
    ]

    @parameterized.expand(dates_to_test)
    @freeze_time(str(today.replace(month=1, day=1)))
    def test_is_recommendation_unlocked_month_start(self, date_to_test, expected):
        self.assertEqual(is_recommendation_unlocked(date_to_test), expected)

    @parameterized.expand(dates_to_test)
    @freeze_time(str(today.replace(month=1, day=31)))
    def test_is_recommendation_unlocked_month_end(self, date_to_test, expected):
        expected = date_to_test == timezone.now().date() or expected
        self.assertEqual(is_recommendation_unlocked(date_to_test), expected)
