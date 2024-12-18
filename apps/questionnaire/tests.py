from django.urls import reverse
from model_bakery.baker import make
from parameterized import parameterized
from rest_framework import status

from apps.questionnaire import DailyBusiness
from apps.questionnaire.models import UserQuestionnaire
from apps.utils.error_codes import Errors
from apps.utils.tests_utils import BaseTestCase


class QuestionnaireTestCase(BaseTestCase):
    def test_questionnaire_record_gets_created(self):
        url = reverse("questionnaire-list")
        data = {
            "is_logging_menstruation": True,
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "female_power_date": "2020-01-01",
            "contraceptive_pill": "ON_BIRTH_CONTROL",
        }

        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        user_questionnaire_record = UserQuestionnaire.objects.get(user=self.user)
        self.assertTrue(user_questionnaire_record)
        self.assertEqual(response.json()["id"], str(user_questionnaire_record.id))
        self.assertEqual(response.json()["skin_goal"], user_questionnaire_record.skin_goal)
        self.assertEqual(response.json()["feeling_today"], user_questionnaire_record.feeling_today)
        self.assertEqual(response.json()["age"], user_questionnaire_record.age)
        self.assertEqual(response.json()["gender"], user_questionnaire_record.gender)
        self.assertTrue(response.json()["is_logging_menstruation"])
        self.assertEqual(
            response.json()["female_power_date"],
            user_questionnaire_record.female_power_date.strftime("%Y-%m-%d"),
        )
        self.assertEqual(
            response.json()["contraceptive_pill"],
            user_questionnaire_record.contraceptive_pill,
        )
        self.assertIsNone(response.json()["stopped_birth_control_date"])

    def test_questionnaire_for_the_user_already_exists(self):
        make(
            UserQuestionnaire,
            user=self.user,
            is_logging_menstruation=True,
            skin_goal="OVERALL_SKIN_HEALTH",
            feeling_today="MEHHH",
            age="AGE_12_16",
            gender="FEMALE",
            female_power_date="2020-01-01",
            contraceptive_pill="ON_BIRTH_CONTROL",
        )
        data = {
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "female_power_date": "2020-01-01",
            "contraceptive_pill": "ON_BIRTH_CONTROL",
        }
        url = reverse("questionnaire-list")

        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            Errors.QUESTIONNAIRE_ALREADY_EXISTS_FOR_THIS_USER.value,
        )

    def test_user_logging_menstruation_must_have_female_power_date(self):
        url = reverse("questionnaire-list")
        data = {
            "is_logging_menstruation": True,
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "contraceptive_pill": "ON_BIRTH_CONTROL",
        }
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            Errors.MENSTRUATING_PERSON_HAS_TO_PROVIDE_A_POWER_DATE.value,
        )

    def test_user_logging_menstruation_must_have_contraceptive_pill_answer(self):
        url = reverse("questionnaire-list")
        data = {
            "is_logging_menstruation": True,
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "female_power_date": "2020-01-01",
        }
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            Errors.MENSTRUATING_PERSON_HAS_TO_PROVIDE_A_CONTRACEPTIVE_PILL_ANSWER.value,
        )

    def test_user_logging_menstruation_with_stopped_birth_control_does_not_have_to_have_a_corresponding_date(
        self,
    ):
        url = reverse("questionnaire-list")
        data = {
            "is_logging_menstruation": True,
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "female_power_date": "2020-01-01",
            "contraceptive_pill": "STOPPED_BIRTH_CONTROL",
        }
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.json()["contraceptive_pill"], "STOPPED_BIRTH_CONTROL")
        self.assertIsNone(response.json()["stopped_birth_control_date"])

    def test_female_power_date_has_to_be_in_past(self):
        url = reverse("questionnaire-list")
        data = {
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "is_logging_menstruation": True,
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "female_power_date": "3020-01-01",
            "contraceptive_pill": "ON_BIRTH_CONTROL",
        }

        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(
            response.json()["female_power_date"][0],
            Errors.FUTURE_DATE_NOT_ALLOWED.value,
        )

    def test_save_make_up_field(self):
        questionnaire = make(
            UserQuestionnaire,
            user=self.user,
            skin_goal="OVERALL_SKIN_HEALTH",
            feeling_today="MEHHH",
            age="AGE_12_16",
            gender="FEMALE",
            is_logging_menstruation=True,
            female_power_date="2020-01-01",
            contraceptive_pill="ON_BIRTH_CONTROL",
            skin_type="NORMAL_SKIN",
            skin_feel="SENSITIVE",
            expectations="ASAP",
            diet_balance="BALANCED",
            diet="DIARY_FREE",
            guilty_pleasures=["COFFEE"],
            easily_stressed="MODERATE",
            hours_of_sleep="7",
            exercise_days_a_week="1",
        )
        self.assertFalse(questionnaire.make_up)

        data = {"make_up": True}
        url = reverse("questionnaire-add-make-up", kwargs={"pk": questionnaire.id})
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["make_up"], True)

    def test_update_make_up_field(self):
        questionnaire = make(
            UserQuestionnaire,
            user=self.user,
            skin_goal="OVERALL_SKIN_HEALTH",
            feeling_today="MEHHH",
            age="AGE_12_16",
            gender="FEMALE",
            is_logging_menstruation=True,
            female_power_date="2020-01-01",
            contraceptive_pill="ON_BIRTH_CONTROL",
            skin_type="NORMAL_SKIN",
            skin_feel="SENSITIVE",
            expectations="ASAP",
            diet_balance="BALANCED",
            diet="DIARY_FREE",
            guilty_pleasures=["COFFEE"],
            easily_stressed="MODERATE",
            hours_of_sleep="7",
            exercise_days_a_week="1",
            make_up=True,
        )
        data = {"make_up": False}
        url = reverse("questionnaire-add-make-up", kwargs={"pk": questionnaire.id})
        response = self.put(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["make_up"], False)
        questionnaire.refresh_from_db()
        self.assertEqual(questionnaire.make_up, False)

    def test_partial_update_does_not_work(self):
        self.query_limits["ANY PATCH REQUEST"] = 1
        questionnaire = make(
            UserQuestionnaire,
            user=self.user,
            skin_goal="OVERALL_SKIN_HEALTH",
            feeling_today="MEHHH",
            age="AGE_12_16",
            gender="FEMALE",
            is_logging_menstruation=True,
            female_power_date="2020-01-01",
            contraceptive_pill="ON_BIRTH_CONTROL",
            skin_type="NORMAL_SKIN",
            skin_feel="SENSITIVE",
            expectations="ASAP",
            diet_balance="BALANCED",
            diet="DIARY_FREE",
            guilty_pleasures=["COFFEE"],
            easily_stressed="MODERATE",
            hours_of_sleep="7",
            exercise_days_a_week="1",
        )
        self.assertFalse(questionnaire.make_up)

        data = {"make_up": True}
        url = reverse("questionnaire-detail", kwargs={"pk": questionnaire.id})
        response = self.patch(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.json(), Errors.PARTIAL_UPDATE_DISABLED.value)

    def test_questionnaire_with_stopped_birth_control_date_not_provided(self):
        url = reverse("questionnaire-list")
        data = {
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "is_logging_menstruation": True,
            "female_power_date": "2020-01-01",
            "contraceptive_pill": "NEVER_BEEN_ON_IT",
            "skin_type": "DRY_SKIN",
            "skin_feel": "SENSITIVE",
            "expectations": "ASAP",
            "diet_balance": "BALANCED",
            "diet": "LOW_CARB",
            "guilty_pleasures": ["JUNK_FOOD_AND_SWEETS"],
            "easily_stressed": "YES",
            "hours_of_sleep": "7",
            "exercise_days_a_week": "TWO",
        }
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_questionnaire = UserQuestionnaire.objects.get(user=self.user)
        self.assertEqual(user_questionnaire.stopped_birth_control_date, None)

    def test_questionnaire_with_smoking_preferences_data_not_provided(self):
        url = reverse("questionnaire-list")
        data = {
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "MALE",
            "contraceptive_pill": "",
            "skin_type": "DRY_SKIN",
            "skin_feel": "SENSITIVE",
            "expectations": "ASAP",
            "diet_balance": "BALANCED",
            "diet": "LOW_CARB",
            "guilty_pleasures": ["JUNK_FOOD_AND_SWEETS"],
            "easily_stressed": "YES",
            "hours_of_sleep": "7",
            "exercise_days_a_week": "SIX_PLUS",
        }
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_questionnaire = UserQuestionnaire.objects.get(user=self.user)
        self.assertEqual(user_questionnaire.smoking_preferences, "")

    def test_update_questionnaire_with_smoking_preferences_data(self):
        questionnaire = make(
            UserQuestionnaire,
            user=self.user,
            skin_goal="OVERALL_SKIN_HEALTH",
            feeling_today="MEHHH",
            age="AGE_12_16",
            gender="FEMALE",
            is_logging_menstruation=False,
            skin_type="NORMAL_SKIN",
            skin_feel="SENSITIVE",
            expectations="ASAP",
            diet_balance="BALANCED",
            diet="DIARY_FREE",
            guilty_pleasures=["COFFEE"],
            easily_stressed="MODERATE",
            hours_of_sleep="7",
            exercise_days_a_week="1",
            make_up=True,
        )
        data = {
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "is_logging_menstruation": False,
            "contraceptive_pill": "",
            "skin_type": "DRY_SKIN",
            "skin_feel": "SENSITIVE",
            "expectations": "ASAP",
            "diet_balance": "BALANCED",
            "diet": "LOW_CARB",
            "guilty_pleasures": ["JUNK_FOOD_AND_SWEETS"],
            "easily_stressed": "YES",
            "hours_of_sleep": "7",
            "exercise_days_a_week": "SIX_PLUS",
            "smoking_preferences": "ANXIOUS_SMOKER",
        }
        url = reverse("questionnaire-detail", kwargs={"pk": questionnaire.id})
        response = self.put(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        questionnaire.refresh_from_db()
        self.assertEqual(questionnaire.smoking_preferences, "ANXIOUS_SMOKER")

    @parameterized.expand(
        [
            ["post", status.HTTP_201_CREATED, "", "", {}],
            [
                "post",
                status.HTTP_400_BAD_REQUEST,
                ["This field may not be null."],
                "",
                {"daily_busyness": None},
            ],
            ["post", status.HTTP_201_CREATED, "", "", {"daily_busyness": ""}],
            [
                "post",
                status.HTTP_400_BAD_REQUEST,
                ['"Something" is not a valid choice.'],
                "",
                {"daily_busyness": "Something"},
            ],
            [
                "post",
                status.HTTP_201_CREATED,
                DailyBusiness.FULL_TIME,
                DailyBusiness.FULL_TIME,
                {"daily_busyness": DailyBusiness.FULL_TIME},
            ],
            ["put", status.HTTP_200_OK, DailyBusiness.STUDY, DailyBusiness.STUDY, {}],
            [
                "put",
                status.HTTP_400_BAD_REQUEST,
                ["This field may not be null."],
                DailyBusiness.STUDY,
                {"daily_busyness": None},
            ],
            ["put", status.HTTP_200_OK, "", "", {"daily_busyness": ""}],
            [
                "put",
                status.HTTP_400_BAD_REQUEST,
                ['"Something" is not a valid choice.'],
                DailyBusiness.STUDY,
                {"daily_busyness": "Something"},
            ],
            [
                "put",
                status.HTTP_200_OK,
                DailyBusiness.FULL_TIME,
                DailyBusiness.FULL_TIME,
                {"daily_busyness": DailyBusiness.FULL_TIME},
            ],
        ]
    )
    def test_update_questionnaire_with_availability_data(
        self, method, status_code, response_data, db_data, request_data
    ):
        questionnaire_data = {
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "is_logging_menstruation": False,
        }

        if method == "put":
            questionnaire = make(
                UserQuestionnaire, user=self.user, daily_busyness=DailyBusiness.STUDY, **questionnaire_data
            )
            url = reverse("questionnaire-detail", kwargs={"pk": questionnaire.id})
        else:
            url = reverse("questionnaire-list")

        response = getattr(self.authorize(), method)(url, data={**questionnaire_data, **request_data})

        self.assertEqual(response.status_code, status_code, response.data)
        self.assertEqual(response.data.get("daily_busyness", ""), response_data, method)

        if method == "put":
            questionnaire.refresh_from_db()
            self.assertEqual(questionnaire.daily_busyness, db_data)
        else:
            if status_code == status.HTTP_400_BAD_REQUEST:
                self.assertFalse(UserQuestionnaire.objects.filter(user=self.user).exists())
            else:
                questionnaire = UserQuestionnaire.objects.get(id=response.data["id"])
                self.assertEqual(questionnaire.daily_busyness, db_data)

    def test_questionnaire_with_female_power_date_empty(self):
        url = reverse("questionnaire-list")
        data = {
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "is_logging_menstruation": True,
            "contraceptive_pill": "NEVER_BEEN_ON_IT",
            "skin_type": "DRY_SKIN",
            "skin_feel": "SENSITIVE",
            "expectations": "ASAP",
            "diet_balance": "BALANCED",
            "diet": "LOW_CARB",
            "guilty_pleasures": ["JUNK_FOOD_AND_SWEETS"],
            "easily_stressed": "YES",
            "hours_of_sleep": "7",
            "exercise_days_a_week": "ZERO",
        }
        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            Errors.MENSTRUATING_PERSON_HAS_TO_PROVIDE_A_POWER_DATE.value,
        )

    def test_update_male_questionnaire_with_empty_contraceptive_pill_value(self):
        questionnaire = make(
            UserQuestionnaire,
            user=self.user,
            skin_goal="OVERALL_SKIN_HEALTH",
            feeling_today="MEHHH",
            age="AGE_12_16",
            gender="MALE",
            female_power_date=None,
            contraceptive_pill="",
            stopped_birth_control_date=None,
            skin_type="SKIPPED",
            skin_feel="SKIPPED",
            expectations="SKIPPED",
            diet_balance="SKIPPED",
            diet="SKIPPED",
            guilty_pleasures=["SKIPPED"],
            easily_stressed="SKIPPED",
            hours_of_sleep="SKIPPED",
            exercise_days_a_week="SKIPPED",
            smoking_preferences="NON_SMOKER",
        )
        self.assertFalse(questionnaire.contraceptive_pill)

        data = {
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "MALE",
            "contraceptive_pill": "",
            "skin_type": "DRY_SKIN",
            "skin_feel": "SENSITIVE",
            "expectations": "ASAP",
            "diet_balance": "BALANCED",
            "diet": "LOW_CARB",
            "guilty_pleasures": ["JUNK_FOOD_AND_SWEETS"],
            "easily_stressed": "YES",
            "hours_of_sleep": "7",
            "exercise_days_a_week": "SIX_PLUS",
        }
        url = reverse("questionnaire-detail", kwargs={"pk": questionnaire.id})
        response = self.put(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        questionnaire.refresh_from_db()
        self.assertEqual(response.json()["id"], str(questionnaire.id))
        self.assertEqual(response.json()["skin_goal"], questionnaire.skin_goal)
        self.assertEqual(response.json()["feeling_today"], questionnaire.feeling_today)
        self.assertEqual(response.json()["age"], questionnaire.age)
        self.assertEqual(response.json()["gender"], questionnaire.gender)
        self.assertEqual(response.json()["female_power_date"], questionnaire.female_power_date)
        self.assertEqual(response.json()["contraceptive_pill"], questionnaire.contraceptive_pill)
        self.assertIsNone(response.json()["stopped_birth_control_date"])
        self.assertEqual(response.json()["skin_type"], questionnaire.skin_type)
        self.assertEqual(response.json()["skin_feel"], questionnaire.skin_feel)
        self.assertEqual(response.json()["expectations"], questionnaire.expectations)
        self.assertEqual(response.json()["diet_balance"], questionnaire.diet_balance)
        self.assertEqual(response.json()["diet"], questionnaire.diet)
        self.assertEqual(response.json()["guilty_pleasures"], questionnaire.guilty_pleasures)
        self.assertEqual(response.json()["easily_stressed"], questionnaire.easily_stressed)
        self.assertEqual(response.json()["hours_of_sleep"], questionnaire.hours_of_sleep)
        self.assertEqual(response.json()["exercise_days_a_week"], questionnaire.exercise_days_a_week)
        self.assertEqual(response.json()["make_up"], questionnaire.make_up)
        self.assertEqual(response.json()["smoking_preferences"], questionnaire.smoking_preferences)


class QuestionnaireIntegrationTestCase(BaseTestCase):
    def test_questionnaire_record_gets_created_and_later_updated(self):
        url = reverse("questionnaire-list")
        data = {
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "is_logging_menstruation": True,
            "female_power_date": "2020-01-01",
            "contraceptive_pill": "ON_BIRTH_CONTROL",
        }

        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        user_questionnaire_record = UserQuestionnaire.objects.get(user=self.user)
        self.assertTrue(user_questionnaire_record)
        self.assertEqual(response.json()["id"], str(user_questionnaire_record.id))
        self.assertEqual(response.json()["skin_goal"], user_questionnaire_record.skin_goal)
        self.assertEqual(response.json()["feeling_today"], user_questionnaire_record.feeling_today)
        self.assertEqual(response.json()["age"], user_questionnaire_record.age)
        self.assertEqual(response.json()["gender"], user_questionnaire_record.gender)
        self.assertTrue(response.json()["is_logging_menstruation"])
        self.assertEqual(
            response.json()["female_power_date"],
            user_questionnaire_record.female_power_date.strftime("%Y-%m-%d"),
        )
        self.assertEqual(
            response.json()["contraceptive_pill"],
            user_questionnaire_record.contraceptive_pill,
        )
        self.assertIsNone(response.json()["stopped_birth_control_date"])
        self.assertEqual(response.json()["make_up"], None)

        url = reverse("questionnaire-detail", kwargs={"pk": str(user_questionnaire_record.id)})
        data = {
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "is_logging_menstruation": True,
            "female_power_date": "2020-01-01",
            "contraceptive_pill": "ON_BIRTH_CONTROL",
            "skin_type": "DRY_SKIN",
            "skin_feel": "SENSITIVE",
            "expectations": "ASAP",
            "diet_balance": "BALANCED",
            "diet": "LOW_CARB",
            "guilty_pleasures": ["JUNK_FOOD_AND_SWEETS"],
            "easily_stressed": "YES",
            "hours_of_sleep": "7",
            "exercise_days_a_week": "TWO",
            "smoking_preferences": "NON_SMOKER",
        }

        response = self.put(url, data=data)
        user_questionnaire_record.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(user_questionnaire_record)
        self.assertEqual(response.json()["id"], str(user_questionnaire_record.id))
        self.assertEqual(response.json()["skin_goal"], user_questionnaire_record.skin_goal)
        self.assertEqual(response.json()["feeling_today"], user_questionnaire_record.feeling_today)
        self.assertEqual(response.json()["age"], user_questionnaire_record.age)
        self.assertEqual(response.json()["gender"], user_questionnaire_record.gender)
        self.assertTrue(response.json()["is_logging_menstruation"])
        self.assertEqual(
            response.json()["female_power_date"],
            user_questionnaire_record.female_power_date.strftime("%Y-%m-%d"),
        )
        self.assertEqual(
            response.json()["contraceptive_pill"],
            user_questionnaire_record.contraceptive_pill,
        )
        self.assertIsNone(response.json()["stopped_birth_control_date"])
        self.assertEqual(response.json()["skin_type"], user_questionnaire_record.skin_type)
        self.assertEqual(response.json()["skin_feel"], user_questionnaire_record.skin_feel)
        self.assertEqual(response.json()["expectations"], user_questionnaire_record.expectations)
        self.assertEqual(response.json()["diet_balance"], user_questionnaire_record.diet_balance)
        self.assertEqual(response.json()["diet"], user_questionnaire_record.diet)
        self.assertEqual(
            response.json()["guilty_pleasures"],
            user_questionnaire_record.guilty_pleasures,
        )
        self.assertEqual(
            response.json()["easily_stressed"],
            user_questionnaire_record.easily_stressed,
        )
        self.assertEqual(response.json()["hours_of_sleep"], user_questionnaire_record.hours_of_sleep)
        self.assertEqual(
            response.json()["exercise_days_a_week"],
            user_questionnaire_record.exercise_days_a_week,
        )
        self.assertEqual(response.json()["make_up"], None)
        self.assertEqual(
            response.json()["smoking_preferences"],
            user_questionnaire_record.smoking_preferences,
        )
        self.assertTrue(response.json()["is_logging_menstruation"])

    def test_questionnaire_record_gets_created_and_later_updated_with_new_values_for_exercise_days_sleep_hours_and_guilty_pleasures(  # noqa E501
        self,
    ):
        url = reverse("questionnaire-list")
        data = {
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "is_logging_menstruation": True,
            "female_power_date": "2020-01-01",
            "contraceptive_pill": "ON_BIRTH_CONTROL",
        }

        response = self.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        user_questionnaire_record = UserQuestionnaire.objects.get(user=self.user)
        self.assertTrue(user_questionnaire_record)
        self.assertEqual(response.json()["id"], str(user_questionnaire_record.id))
        self.assertEqual(response.json()["skin_goal"], user_questionnaire_record.skin_goal)
        self.assertEqual(response.json()["feeling_today"], user_questionnaire_record.feeling_today)
        self.assertEqual(response.json()["age"], user_questionnaire_record.age)
        self.assertEqual(response.json()["gender"], user_questionnaire_record.gender)
        self.assertTrue(response.json()["is_logging_menstruation"])
        self.assertEqual(
            response.json()["female_power_date"],
            user_questionnaire_record.female_power_date.strftime("%Y-%m-%d"),
        )
        self.assertEqual(
            response.json()["contraceptive_pill"],
            user_questionnaire_record.contraceptive_pill,
        )
        self.assertIsNone(response.json()["stopped_birth_control_date"])
        self.assertEqual(response.json()["make_up"], None)

        url = reverse("questionnaire-detail", kwargs={"pk": str(user_questionnaire_record.id)})
        data = {
            "skin_goal": "OVERALL_SKIN_HEALTH",
            "feeling_today": "MEHHH",
            "age": "AGE_12_16",
            "gender": "FEMALE",
            "is_logging_menstruation": True,
            "female_power_date": "2020-01-01",
            "contraceptive_pill": "ON_BIRTH_CONTROL",
            "skin_type": "DRY_SKIN",
            "skin_feel": "SENSITIVE",
            "expectations": "ASAP",
            "diet_balance": "BALANCED",
            "diet": "LOW_CARB",
            "guilty_pleasures": ["JUNK_FOOD_AND_SWEETS", "IM_INNOCENT"],
            "easily_stressed": "YES",
            "hours_of_sleep": "SEVEN_EIGHT",
            "exercise_days_a_week": "ONE_THREE",
            "smoking_preferences": "NON_SMOKER",
        }

        response = self.put(url, data=data)
        user_questionnaire_record.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(user_questionnaire_record)
        self.assertEqual(response.json()["id"], str(user_questionnaire_record.id))
        self.assertEqual(response.json()["skin_goal"], user_questionnaire_record.skin_goal)
        self.assertEqual(response.json()["feeling_today"], user_questionnaire_record.feeling_today)
        self.assertEqual(response.json()["age"], user_questionnaire_record.age)
        self.assertEqual(response.json()["gender"], user_questionnaire_record.gender)
        self.assertTrue(response.json()["is_logging_menstruation"])
        self.assertEqual(
            response.json()["female_power_date"],
            user_questionnaire_record.female_power_date.strftime("%Y-%m-%d"),
        )
        self.assertEqual(
            response.json()["contraceptive_pill"],
            user_questionnaire_record.contraceptive_pill,
        )
        self.assertIsNone(response.json()["stopped_birth_control_date"])
        self.assertEqual(response.json()["skin_type"], user_questionnaire_record.skin_type)
        self.assertEqual(response.json()["skin_feel"], user_questionnaire_record.skin_feel)
        self.assertEqual(response.json()["expectations"], user_questionnaire_record.expectations)
        self.assertEqual(response.json()["diet_balance"], user_questionnaire_record.diet_balance)
        self.assertEqual(response.json()["diet"], user_questionnaire_record.diet)
        self.assertEqual(
            response.json()["guilty_pleasures"],
            user_questionnaire_record.guilty_pleasures,
        )
        self.assertEqual(
            response.json()["easily_stressed"],
            user_questionnaire_record.easily_stressed,
        )
        self.assertEqual(response.json()["hours_of_sleep"], user_questionnaire_record.hours_of_sleep)
        self.assertEqual(
            response.json()["exercise_days_a_week"],
            user_questionnaire_record.exercise_days_a_week,
        )
        self.assertEqual(response.json()["make_up"], None)
        self.assertEqual(
            response.json()["smoking_preferences"],
            user_questionnaire_record.smoking_preferences,
        )
