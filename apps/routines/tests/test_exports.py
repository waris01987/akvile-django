import datetime

from django.utils import timezone
from model_bakery.baker import make

from apps.questionnaire.models import UserQuestionnaire
from apps.routines import TagCategories
from apps.routines.models import (
    FaceScan,
    FaceScanAnalytics,
    FaceScanSmoothingAnalytics,
    DailyQuestionnaire,
    UserTag,
)
from apps.routines.resources import FaceScanResource, DailyQuestionnaireResource
from apps.utils.tests_utils import BaseTestCase


class FaceScanDataExportTestCase(BaseTestCase):
    def test_data_export(self):
        face_scan = make(FaceScan, user=self.user, id=1, _fill_optional=True)

        face_analytics = make(FaceScanAnalytics, face_scan=face_scan, _fill_optional=True)
        face_smoothing_analytics = make(FaceScanSmoothingAnalytics, face_scan=face_scan, _fill_optional=True)

        resource_obj = FaceScanResource()
        face_scan_resource_headers = resource_obj.get_export_headers()
        face_scan_obj = resource_obj.get_export_queryset().first()
        face_scan_data = resource_obj.export_resource(face_scan_obj)

        generated_data = {key: value for key, value in zip(face_scan_resource_headers, face_scan_data)}
        self.assertEqual(generated_data["id"], face_scan.id)
        self.assertEqual(generated_data["email"], self.user.email)
        self.assertEqual(int(generated_data["analytics_acne"]), face_analytics.acne)
        self.assertEqual(int(generated_data["analytics_lines"]), face_analytics.lines)
        self.assertEqual(int(generated_data["analytics_wrinkles"]), face_analytics.wrinkles)
        self.assertEqual(int(generated_data["analytics_pigmentation"]), face_analytics.pigmentation)
        self.assertEqual(int(generated_data["analytics_translucency"]), face_analytics.translucency)
        self.assertEqual(int(generated_data["analytics_quality"]), face_analytics.quality)
        self.assertEqual(int(generated_data["analytics_eye_bags"]), face_analytics.eye_bags)
        self.assertEqual(int(generated_data["analytics_pores"]), face_analytics.pores)
        self.assertEqual(int(generated_data["analytics_sagging"]), face_analytics.sagging)
        self.assertEqual(int(generated_data["analytics_uniformness"]), face_analytics.uniformness)
        self.assertEqual(int(generated_data["analytics_hydration"]), face_analytics.hydration)
        self.assertEqual(int(generated_data["analytics_redness"]), face_analytics.redness)
        self.assertEqual(bool(generated_data["analytics_is_valid"]), face_analytics.is_valid)
        self.assertEqual(
            int(generated_data["smoothing_analytics_acne"]),
            face_smoothing_analytics.acne,
        )
        self.assertEqual(
            int(generated_data["smoothing_analytics_lines"]),
            face_smoothing_analytics.lines,
        )
        self.assertEqual(
            int(generated_data["smoothing_analytics_wrinkles"]),
            face_smoothing_analytics.wrinkles,
        )
        self.assertEqual(
            int(generated_data["smoothing_analytics_pigmentation"]),
            face_smoothing_analytics.pigmentation,
        )
        self.assertEqual(
            int(generated_data["smoothing_analytics_translucency"]),
            face_smoothing_analytics.translucency,
        )
        self.assertEqual(
            int(generated_data["smoothing_analytics_quality"]),
            face_smoothing_analytics.quality,
        )
        self.assertEqual(
            int(generated_data["smoothing_analytics_eye_bags"]),
            face_smoothing_analytics.eye_bags,
        )
        self.assertEqual(
            int(generated_data["smoothing_analytics_pores"]),
            face_smoothing_analytics.pores,
        )
        self.assertEqual(
            int(generated_data["smoothing_analytics_sagging"]),
            face_smoothing_analytics.sagging,
        )
        self.assertEqual(
            int(generated_data["smoothing_analytics_uniformness"]),
            face_smoothing_analytics.uniformness,
        )
        self.assertEqual(
            int(generated_data["smoothing_analytics_hydration"]),
            face_smoothing_analytics.hydration,
        )
        self.assertEqual(
            int(generated_data["smoothing_analytics_redness"]),
            face_smoothing_analytics.redness,
        )
        self.assertEqual(generated_data["haut_ai_batch_id"], face_scan.haut_ai_batch_id)
        self.assertEqual(generated_data["haut_ai_image_id"], face_scan.haut_ai_image_id)
        self.assertEqual(
            generated_data["created_at"],
            face_scan.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def test_face_scan_export_resource_classes(self):
        resource_classes = FaceScan.export_resource_classes()
        self.assertEqual(list(resource_classes.keys())[0], "face_scans")
        self.assertEqual(resource_classes["face_scans"], ("face scan resources", FaceScanResource))
        resource_values = list(resource_classes.values())
        self.assertEqual(resource_values[0][0], "face scan resources")
        self.assertEqual(resource_values[0][1], FaceScanResource)


class DailyQuestionnaireDataExportTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.user_questionnaire = make(UserQuestionnaire, user=self.user)
        self.user_questionnaire.created_at = timezone.now() - datetime.timedelta(days=8)
        self.user_questionnaire.save()

    def test_data_export(self):
        nutrition_tags = make(UserTag, category=TagCategories.NUTRITION, _quantity=2)
        skin_care_tags = make(UserTag, category=TagCategories.SKIN_CARE, _quantity=2)
        well_being_tags = make(UserTag, category=TagCategories.WELL_BEING, _quantity=2)
        questionnaire = make(
            DailyQuestionnaire,
            id=1,
            user=self.user,
            skin_feel="SENSITIVE",
            diet_today="BALANCED",
            water=3,
            stress_levels="RELAXED",
            exercise_hours="TWO_HOURS",
            life_happened=["COFFEE", "JUNK_FOOD_AND_SWEETS"],
            feeling_today="LOVE_IT",
            hours_of_sleep=8,
            sleep_quality="WELL",
            something_special=["VACATION"],
        )
        questionnaire.tags_for_skin_care.add(*skin_care_tags)
        questionnaire.tags_for_well_being.add(*well_being_tags)
        questionnaire.tags_for_nutrition.add(*nutrition_tags)
        questionnaire.save()

        resource_obj = DailyQuestionnaireResource()
        questionnaire_resource_headers = resource_obj.get_export_headers()
        questionnaire_obj = resource_obj.get_export_queryset().first()
        questionnaire_data = resource_obj.export_resource(questionnaire_obj)

        generated_data = {key: value for key, value in zip(questionnaire_resource_headers, questionnaire_data)}
        self.assertEqual(generated_data["id"], questionnaire.id)
        self.assertEqual(generated_data["email"], self.user.email)
        self.assertEqual(generated_data["skin_feel"], questionnaire.skin_feel)
        self.assertEqual(generated_data["diet_today"], questionnaire.diet_today)
        self.assertEqual(generated_data["water"], questionnaire.water)
        self.assertEqual(generated_data["life_happened"].split(","), questionnaire.life_happened)
        self.assertEqual(generated_data["stress_levels"], questionnaire.stress_levels)
        self.assertEqual(generated_data["exercise_hours"], questionnaire.exercise_hours)
        self.assertEqual(generated_data["feeling_today"], questionnaire.feeling_today)
        self.assertEqual(generated_data["hours_of_sleep"], questionnaire.hours_of_sleep)
        self.assertEqual(generated_data["sleep_quality"], questionnaire.sleep_quality)
        self.assertEqual(
            generated_data["something_special"].split(","),
            questionnaire.something_special,
        )
        self.assertEqual(
            generated_data["created_at"],
            questionnaire.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.assertEqual(
            generated_data["skin_care_tags"].split(","),
            list(questionnaire.tags_for_skin_care.values_list("name", flat=True)),
        )
        self.assertEqual(
            generated_data["well_being_tags"].split(","),
            list(questionnaire.tags_for_well_being.values_list("name", flat=True)),
        )
        self.assertEqual(
            generated_data["nutrition_tags"].split(","),
            list(questionnaire.tags_for_nutrition.values_list("name", flat=True)),
        )

    def test_daily_questionnaire_export_resource_classes(self):
        resource_classes = DailyQuestionnaire.export_resource_classes()
        self.assertEqual(list(resource_classes.keys())[0], "daily_questionnaires")
        self.assertEqual(
            resource_classes["daily_questionnaires"],
            ("daily questionnaire resources", DailyQuestionnaireResource),
        )
        resource_values = list(resource_classes.values())
        self.assertEqual(resource_values[0][0], "daily questionnaire resources")
        self.assertEqual(resource_values[0][1], DailyQuestionnaireResource)
