from typing import Optional

from dal import autocomplete
from django.contrib import admin
from django.db.models import JSONField, QuerySet  # type: ignore
from django.forms import Textarea, ModelForm
from django.utils.safestring import mark_safe
from import_export_celery.admin_actions import create_export_job_action
import nested_admin
from rest_framework.request import Request

from apps.routines.filters import IsCompletedFilter
from apps.routines.models import (
    Routine,
    EveningQuestionnaire,
    MorningQuestionnaire,
    FaceScan,
    FaceScanAnalytics,
    FaceScanSmoothingAnalytics,
    DailyQuestionnaire,
    DailyStatistics,
    FaceScanComment,
    UserTag,
    HealthCareEvent,
    Prediction,
    StatisticsPurchase,
    PurchaseHistory,
    DailyProductGroup,
    DailyProduct,
    DailyProductTemplate,
    ScrapedProduct,
    UserScrapedProduct,
    Recommendation,
)
from apps.routines.resources import DailyQuestionnaireResource, FaceScanResource
from apps.routines.tasks import send_reminder_notification_for_appointments
from apps.utils.mixins import CeleryExportMixin


class DailyProductForm(ModelForm):
    brand = autocomplete.Select2ListCreateChoiceField(
        choice_list=lambda: DailyProduct.get_field_values("brand"),
        widget=autocomplete.ListSelect2(url="daily-product-brand-autocomplete"),
        required=False,
    )
    name = autocomplete.Select2ListCreateChoiceField(
        choice_list=lambda: DailyProduct.get_field_values("name"),
        widget=autocomplete.ListSelect2(url="daily-product-name-autocomplete"),
        required=False,
    )
    ingredients = autocomplete.Select2ListCreateChoiceField(
        choice_list=lambda: DailyProduct.get_field_values("ingredients"),
        widget=autocomplete.ListSelect2(url="daily-product-ingredients-autocomplete"),
        required=False,
    )

    class Meta:
        fields = [
            "image",
            "brand",
            "name",
            "ingredients",
            "size",
            "type",
            "is_medication",
            "product_info",
            "review_score",
            "satisfaction_score",
            "preference_score",
            "efficiency_score",
            "accessibility_score",
            "easy_to_use_score",
            "cost_score",
            "image_parse_fail",
            "connect_scrapped_fail",
            "brand_updated",
            "parsed_by_chat_gpt_data",
        ]
        model = DailyProduct


@admin.register(Routine)
class RoutineAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at"]
    search_fields = ["user__email", "created_at"]

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(EveningQuestionnaire)
class EveningQuestionnaireAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at"]
    search_fields = ["user__email", "created_at"]

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(MorningQuestionnaire)
class MorningQuestionnaireAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at"]
    search_fields = ["user__email", "created_at"]

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DailyQuestionnaire)
class DailyQuestionnaireAdmin(CeleryExportMixin, admin.ModelAdmin):
    resource_class = DailyQuestionnaireResource
    list_display = ["user", "created_at"]
    search_fields = ["user__email", "created_at"]
    actions = (create_export_job_action,)

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DailyStatistics)
class DailyStatisticsAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "skin_care",
        "well_being",
        "nutrition",
        "routine_count_status",
        "date",
    ]
    search_fields = ["user__email", "date"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


class FaceScanAnalyticsInline(nested_admin.NestedTabularInline):
    model = FaceScanAnalytics
    extra = 0
    formfield_overrides = {JSONField: {"widget": Textarea(attrs={"readonly": True})}}

    def get_readonly_fields(self, request, obj=None):
        # removed `raw_data` field to override the form widget to take effect
        return [field.name for field in FaceScanAnalytics._meta.get_fields() if field.name != "raw_data"]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class FaceScanSmoothingAnalyticsInline(nested_admin.NestedTabularInline):
    model = FaceScanSmoothingAnalytics
    extra = 0
    readonly_fields = [field.name for field in FaceScanSmoothingAnalytics._meta.get_fields()]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class FaceScanCommentInline(admin.TabularInline):
    model = FaceScanComment
    extra = 0


class DailyProductAdminInline(admin.TabularInline):
    model = DailyProduct
    extra = 0
    form = DailyProductForm

    def has_delete_permission(self, request: Request, obj: Optional[DailyProduct] = None) -> bool:
        return False


@admin.register(DailyProductGroup)
class DailyProductGroupAdmin(admin.ModelAdmin):
    inlines = [DailyProductAdminInline]
    list_display = ["id", "user", "country", "age", "completed"]
    search_fields = ["user__email", "country", "user__questionnaire__age"]
    list_filter = [IsCompletedFilter]
    readonly_fields = ["user", "age"]
    actions = ["clear_product_fields"]

    @admin.action(description="Clear daily products of selected daily product groups")  # type: ignore[attr-defined]
    def clear_product_fields(self, request: Request, queryset: QuerySet[DailyProductGroup]) -> None:
        DailyProduct.objects.filter(group__in=queryset).update(**{field: "" for field in DailyProduct.CLEARABLE_FIELDS})

    @admin.display(boolean=True)  # type: ignore
    def completed(self, obj):
        return obj.completed

    @admin.display()  # type: ignore
    def age(self, obj):
        questionnaire = getattr(obj.user, "questionnaire", None)
        return questionnaire.age if questionnaire else None


@admin.register(DailyProduct)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "group",
        "image",
        "type",
        "name",
        "brand",
        "ingredients",
        "size",
        "completed",
        "is_medication",
        "product_info",
    ]
    search_fields = ["group__user__email", "name", "brand", "ingredients", "size"]
    list_filter = [IsCompletedFilter, "type", "is_medication"]
    form = DailyProductForm
    actions = ["clear_fields"]

    @admin.action(description="Clear selected daily products")  # type: ignore[attr-defined]
    def clear_fields(self, request: Request, queryset: QuerySet[DailyProduct]) -> None:
        queryset.update(**{field: "" for field in DailyProduct.CLEARABLE_FIELDS})

    @admin.display(boolean=True)  # type: ignore
    def completed(self, obj):
        return obj.completed

    def has_delete_permission(self, request: Request, obj: Optional[DailyProduct] = None) -> bool:
        return False


@admin.register(ScrapedProduct)
class ScrapedProductAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "brand",
        "title",
        "url",
        "job_id",
        "status_code",
        "is_medication",
        "recommended_product",
    ]
    list_filter = ["recommended_product"]


@admin.register(UserScrapedProduct)
class UserScrapedProductAdmin(admin.ModelAdmin):
    list_display = ["product", "user", "want", "have"]
    search_fields = ["product__title", "user__email"]
    list_filter = ["want", "have"]


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "category",
        "current_index",
        "previuos_indexes",
        "is_featured",
    ]


@admin.register(DailyProductTemplate)
class DailyProductTemplateAdmin(admin.ModelAdmin):
    list_display = ["id", "brand", "name", "ingredients"]


@admin.register(FaceScan)
class FaceScanAdmin(CeleryExportMixin, admin.ModelAdmin):
    resource_class = FaceScanResource
    list_display = ["thumbnail_preview", "user", "has_comment"]
    search_fields = ["user__email", "created_at"]
    inlines = [
        FaceScanAnalyticsInline,
        FaceScanSmoothingAnalyticsInline,
        FaceScanCommentInline,
    ]
    readonly_fields = ["user", "haut_ai_image_id", "haut_ai_batch_id"]
    list_filter = ["updated_sagging"]
    actions = (create_export_job_action,)

    @admin.display(description="preview")  # type: ignore
    def thumbnail_preview(self, obj):
        """Thumbnail image preview for face scan"""
        if obj.image:
            return mark_safe('<img src="{}" width="80" height="100" />'.format(obj.image.url))  # noqa: S308,S703
        return "No Image"

    @admin.display(description="comment")  # type: ignore
    def has_comment(self, obj):
        """Comment for face scan"""
        return bool(obj.face_scan_comments)


@admin.register(UserTag)
class UserTagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "category", "user", "created_at"]
    search_fields = ["user__email", "created_at"]
    ordering = ["-user", "-created_at"]
    readonly_fields = [
        "user",
    ]


@admin.register(HealthCareEvent)
class HealthCareEventAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "event_type",
        "name",
        "medication_type",
        "start_date",
        "duration",
        "time",
        "created_at",
    ]
    read_only_fields = list_display
    search_fields = ["user__email", "start_date"]
    actions = [
        "send_reminder_notification_for_appointment_event",
    ]

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.action(description="Manually send appointment event reminder notification")  # type: ignore[attr-defined]
    def send_reminder_notification_for_appointment_event(self, request, queryset) -> None:
        """Send appointment event reminder push notification manually"""
        send_reminder_notification_for_appointments(queryset.values_list("id", flat=True))


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "prediction_type", "created_at"]
    search_fields = ["user__email", "date"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


class PurchaseHistoryInline(admin.TabularInline):
    model = PurchaseHistory
    readonly_fields = (
        "purchase",
        "status",
        "created_at",
    )
    fields = readonly_fields
    extra = 0

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(StatisticsPurchase)
class StatisticsPurchaseAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "store_product",
        "status",
        "purchase_started_on",
        "purchase_ends_after",
        "total_transactions",
    ]
    search_fields = ["user__email", "store_product__name", "store_product__sku"]
    inlines = [PurchaseHistoryInline]
    readonly_fields = ["user"]

    def has_delete_permission(self, request: Request, obj: Optional[StatisticsPurchase] = None):
        return False
