from fcm_django.models import FCMDevice
from model_bakery.baker import make

from apps.content import CategoryName
from apps.content.models import Article, Category, UserArticle
from apps.orders.models import Order
from apps.questionnaire import (
    SkinGoal,
    FeelingToday,
    Age,
    Gender,
    ContraceptivePill,
    SkinType,
    SkinFeel,
    ExpectationsForFirstResults,
    DietBalance,
    Diet,
    GuiltyPleasures,
    EasilyStressedAndUpset,
    HoursOfSleep,
    ExerciseDaysAWeek,
)
from apps.questionnaire.models import UserQuestionnaire
from apps.routines import RoutineType
from apps.routines.models import Routine, FaceScan, DailyQuestionnaire
from apps.users.models import User
from apps.users.resources import UserResource
from apps.utils.tests_utils import BaseTestCase


class UserDataExportTestCase(BaseTestCase):
    def test_data_export(self):  # noqa: CFQ001
        make(
            UserQuestionnaire,
            user=self.user,
            skin_goal=SkinGoal.OVERALL_SKIN_HEALTH.value,
            feeling_today=FeelingToday.WELL.value,
            age=Age.AGE_32_36.value,
            gender=Gender.FEMALE.value,
            female_power_date="2000-01-01",
            contraceptive_pill=ContraceptivePill.ON_BIRTH_CONTROL.value,
            stopped_birth_control_date=None,
            menstruating_person=True,
            skin_type=SkinType.DRY_SKIN.value,
            skin_feel=SkinFeel.DEHYDRATED.value,
            expectations=ExpectationsForFirstResults.ASAP.value,
            diet_balance=DietBalance.BALANCED.value,
            diet=Diet.DIARY_FREE.value,
            guilty_pleasures=[GuiltyPleasures.SKIPPED.value],
            easily_stressed=EasilyStressedAndUpset.MODERATE.value,
            hours_of_sleep=HoursOfSleep.EIGHT.value,
            exercise_days_a_week=ExerciseDaysAWeek.TWO.value,
            make_up=True,
        )

        make(Routine, user=self.user, routine_type=RoutineType.AM.value, _quantity=2)
        make(Routine, user=self.user, routine_type=RoutineType.PM.value, _quantity=4)
        last_routine_date = Routine.objects.latest("created_at").created_at

        make(DailyQuestionnaire, user=self.user, _quantity=6)
        last_daily_questionnaire_date = DailyQuestionnaire.objects.latest("created_at").created_at

        make(FaceScan, user=self.user, _quantity=3)
        last_f_scan_date = FaceScan.objects.latest("created_at").created_at

        make(Order, user=self.user, total_price=120)
        make(Order, user=self.user, total_price=130)
        make(Order, user=self.user, total_price=140)
        last_order_date = Order.objects.latest("shopify_order_date").shopify_order_date

        category = make(Category, name=CategoryName.CORE_PROGRAM.value)
        # make two articles that will be marked as read
        article_1 = make(Article, is_published=True, category=category)
        article_2 = make(Article, is_published=True, category=category)
        user_article1 = UserArticle.objects.get(article=article_1)
        user_article2 = UserArticle.objects.get(article=article_2)
        user_article1.is_read = True
        user_article2.is_read = True
        user_article1.save()
        user_article2.save()

        # make one unread article
        make(Article, category=category)

        # make one FCM Device
        make(FCMDevice, user=self.user, type="android")

        user = UserResource().get_export_queryset().first()

        self.assertEqual(user.questionnaire.skin_goal, "OVERALL_SKIN_HEALTH")
        self.assertEqual(user.questionnaire.feeling_today, "WELL")
        self.assertEqual(user.questionnaire.age, "AGE_32_36")
        self.assertEqual(user.questionnaire.gender, "FEMALE")
        self.assertEqual(user.questionnaire.female_power_date.strftime("%Y-%m-%d"), "2000-01-01")
        self.assertEqual(user.questionnaire.contraceptive_pill, "ON_BIRTH_CONTROL")
        self.assertEqual(user.questionnaire.stopped_birth_control_date, None)
        self.assertEqual(user.questionnaire.menstruating_person, True)
        self.assertEqual(user.questionnaire.skin_type, "DRY_SKIN")
        self.assertEqual(user.questionnaire.skin_feel, "DEHYDRATED")
        self.assertEqual(user.questionnaire.expectations, "ASAP")
        self.assertEqual(user.questionnaire.diet_balance, "BALANCED")
        self.assertEqual(user.questionnaire.diet, "DIARY_FREE")
        self.assertEqual(user.questionnaire.guilty_pleasures, ["SKIPPED"])
        self.assertEqual(user.questionnaire.easily_stressed, "MODERATE")
        self.assertEqual(user.questionnaire.hours_of_sleep, "8")
        self.assertEqual(user.questionnaire.exercise_days_a_week, "TWO")
        self.assertEqual(user.questionnaire.make_up, True)

        self.assertEqual(user.total_routines, 6)
        self.assertEqual(user.pm_routines, 4)
        self.assertEqual(user.am_routines, 2)
        self.assertEqual(user.last_routine, last_routine_date)

        self.assertEqual(user.f_scan_count, 3)
        self.assertEqual(user.last_f_scan, last_f_scan_date)

        self.assertEqual(user.total_daily_questionnaires, 6)
        self.assertEqual(user.last_daily_questionnaire, last_daily_questionnaire_date)

        self.assertEqual(user.total_read_articles, 2)

        self.assertEqual(user.total_amount_spent, 390)
        self.assertEqual(user.total_orders_made, 3)
        self.assertEqual(user.last_order_date, last_order_date)
        self.assertEqual(user.last_order_amount, 140)
        self.assertEqual(user.device_type, "android")

    def test_user_export_resource_classes(self):
        resource_classes = User.export_resource_classes()
        self.assertEqual(list(resource_classes.keys())[0], "users")
        self.assertEqual(resource_classes["users"], ("user resources", UserResource))
        resource_values = list(resource_classes.values())
        self.assertEqual(resource_values[0][0], "user resources")
        self.assertEqual(resource_values[0][1], UserResource)
