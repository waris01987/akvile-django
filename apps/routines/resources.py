from import_export import resources, fields

from apps.routines.models import FaceScan, DailyQuestionnaire


class FaceScanResource(resources.ModelResource):
    email = fields.Field("user__email", readonly=True)
    # Fields from FaceScanAnalytics
    analytics_acne = fields.Field("analytics__acne", readonly=True)
    analytics_lines = fields.Field("analytics__lines", readonly=True)
    analytics_wrinkles = fields.Field("analytics__wrinkles", readonly=True)
    analytics_pigmentation = fields.Field("analytics__pigmentation", readonly=True)
    analytics_translucency = fields.Field("analytics__translucency", readonly=True)
    analytics_quality = fields.Field("analytics__quality", readonly=True)
    analytics_eye_bags = fields.Field("analytics__eye_bags", readonly=True)
    analytics_pores = fields.Field("analytics__pores", readonly=True)
    analytics_sagging = fields.Field("analytics__sagging", readonly=True)
    analytics_uniformness = fields.Field("analytics__uniformness", readonly=True)
    analytics_hydration = fields.Field("analytics__hydration", readonly=True)
    analytics_redness = fields.Field("analytics__redness", readonly=True)
    analytics_is_valid = fields.Field("analytics__is_valid", readonly=True)
    # Fields from FaceScanSmoothingAnalytics
    smoothing_analytics_acne = fields.Field("smoothing_analytics__acne", readonly=True)
    smoothing_analytics_lines = fields.Field("smoothing_analytics__lines", readonly=True)
    smoothing_analytics_wrinkles = fields.Field("smoothing_analytics__wrinkles", readonly=True)
    smoothing_analytics_pigmentation = fields.Field("smoothing_analytics__pigmentation", readonly=True)
    smoothing_analytics_translucency = fields.Field("smoothing_analytics__translucency", readonly=True)
    smoothing_analytics_quality = fields.Field("smoothing_analytics__quality", readonly=True)
    smoothing_analytics_eye_bags = fields.Field("smoothing_analytics__eye_bags", readonly=True)
    smoothing_analytics_pores = fields.Field("smoothing_analytics__pores", readonly=True)
    smoothing_analytics_sagging = fields.Field("smoothing_analytics__sagging", readonly=True)
    smoothing_analytics_uniformness = fields.Field("smoothing_analytics__uniformness", readonly=True)
    smoothing_analytics_hydration = fields.Field("smoothing_analytics__hydration", readonly=True)
    smoothing_analytics_redness = fields.Field("smoothing_analytics__redness", readonly=True)

    class Meta:
        model = FaceScan
        fields = [
            "id",
            "haut_ai_batch_id",
            "haut_ai_image_id",
            "created_at",
        ]
        export_order = ["id", "email"]
        chunk_size = 5000

    def get_export_queryset(self):
        return self.Meta.model.objects.select_related("user").prefetch_related("analytics", "smoothing_analytics")


class DailyQuestionnaireResource(resources.ModelResource):
    email = fields.Field("user__email", readonly=True)
    skin_care_tags = fields.Field()
    well_being_tags = fields.Field()
    nutrition_tags = fields.Field()

    class Meta:
        model = DailyQuestionnaire
        fields = [
            "id",
            "skin_feel",
            "diet_today",
            "water",
            "life_happened",
            "stress_levels",
            "exercise_hours",
            "feeling_today",
            "hours_of_sleep",
            "sleep_quality",
            "something_special",
            "created_at",
        ]
        export_order = ["id", "email"]
        chunk_size = 5000

    def get_export_queryset(self):
        qs = self.Meta.model.objects.select_related("user").prefetch_related(
            "tags_for_skin_care", "tags_for_well_being", "tags_for_nutrition"
        )
        return qs

    def dehydrate_skin_care_tags(self, questionnaires: DailyQuestionnaire) -> str:
        return ",".join(questionnaires.tags_for_skin_care.values_list("name", flat=True))

    def dehydrate_well_being_tags(self, questionnaires: DailyQuestionnaire) -> str:
        return ",".join(questionnaires.tags_for_well_being.values_list("name", flat=True))

    def dehydrate_nutrition_tags(self, questionnaires: DailyQuestionnaire) -> str:
        return ",".join(questionnaires.tags_for_nutrition.values_list("name", flat=True))
