import calendar
import datetime
import json
import logging
from typing import Optional, no_type_check, Union

from dal import autocomplete
from django.conf import settings
from django.db import transaction
from django.db.models import (
    Subquery,
    OuterRef,
    Avg,
    F,
    IntegerField,
    Q,
    Prefetch,
    Value,
    QuerySet,
)
from django.db.models.functions import Coalesce, Concat
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, exceptions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet, ReadOnlyModelViewSet

from apps.home.models import (
    SiteConfiguration,
    FaceScanCommentTemplateTranslation,
    PredictionTemplateTranslation,
)
from apps.routines import (
    FaceScanNotificationTypes,
    TagCategories,
    HealthCareEventTypes,
    PurchaseStatus,
)
from apps.routines.filters import RoutineFilter, ScrapedProductFilter
from apps.routines.haut_ai import (
    get_auth_info,
    get_smoothing_results,
    get_image_results,
    build_orm_analytics_model,
    build_orm_smoothing_analytics_model,
)
from apps.routines.models import (
    FaceScan,
    Routine,
    MorningQuestionnaire,
    EveningQuestionnaire,
    FaceScanAnalytics,
    FaceScanSmoothingAnalytics,
    DailyQuestionnaire,
    DailyStatistics,
    FaceScanComment,
    Prediction,
    UserTag,
    StatisticsPurchase,
    DailyProductGroup,
    DailyProduct,
    DailyProductTemplate,
    Recommendation,
    UserScrapedProduct,
    ScrapedProduct,
)
from apps.routines.progresses import generate_monthly_progress
from apps.routines.purchases import (
    process_statistics_purchase_play_store_notifications,
    process_statistics_purchase_app_store_notification,
    generate_unified_receipt,
)
from apps.routines.schemas import (
    statistics_overview_schema,
    monthly_progress_schema,
    want_have_schema,
)
from apps.routines.serializers import (
    FaceScanSerializer,
    RoutineSerializer,
    MorningQuestionnaireSerializer,
    EveningQuestionnaireSerializer,
    FaceScanAnalyticsSerializer,
    FaceScanSmoothingAnalyticsSerializer,
    DailyQuestionnaireSerializer,
    StatisticsSerializer,
    FaceScanCommentSerializer,
    PredictionSerializer,
    UserTagSerializer,
    MedicationEventSerializer,
    AppointmentEventSerializer,
    MenstruationEventSerializer,
    StatisticsPurchaseSerializer,
    DailyProductGroupSerializer,
    DailyProductSerializer,
    RecommendationSerializer,
    ImportScrappedProductsSerializer,
    DailyProductSetReviewSerializer,
    ScrappedProductSerializer,
    DailyProductCreateSerializer,
)
from apps.utils.error_codes import Errors
from apps.utils.helpers import decode_data, parse_jwt
from apps.utils.tasks import generate_and_send_notification, import_products_from_amazon

LOGGER = logging.getLogger("app")


class DailyProductAutocompleteMixin:
    field = None

    def get_list(self) -> set[str]:
        return set(DailyProduct.objects.values_list(self.field, flat=True))

    def create(self, text: str) -> str:
        return text

    def get(self, request: Request, *args: list, **kwargs: dict) -> JsonResponse:
        return self._check_permissions() or super().get(request, *args, **kwargs)  # type: ignore

    def post(self, request: Request, *args: list, **kwargs: dict) -> JsonResponse:
        return self._check_permissions() or super().post(request, *args, **kwargs)  # type: ignore

    def _check_permissions(self) -> Optional[JsonResponse]:  # type: ignore
        if not (self.request.user.is_staff or self.request.user.is_superuser):  # type: ignore
            return JsonResponse({"detail": "Admin access only"}, status=status.HTTP_403_FORBIDDEN)


class RoutineViewSet(ModelViewSet):
    serializer_class = RoutineSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = RoutineFilter

    def get_queryset(self):
        return Routine.objects.filter(user=self.request.user)

    @action(
        methods=["get"],
        detail=False,
        url_path="latest-routine",
        url_name="latest-routine",
    )
    def latest_routine(self, request, *args, **kwargs):
        try:
            latest_routine = self.get_queryset().latest("created_at").created_at
        except Routine.DoesNotExist:
            latest_routine = None
        return Response({"latest_routine": latest_routine})


class MorningQuestionnaireViewSet(ModelViewSet):
    serializer_class = MorningQuestionnaireSerializer

    def get_queryset(self):
        return MorningQuestionnaire.objects.filter(user=self.request.user)


class EveningQuestionnaireViewSet(ModelViewSet):
    serializer_class = EveningQuestionnaireSerializer

    def get_queryset(self):
        return EveningQuestionnaire.objects.filter(user=self.request.user)


class DailyQuestionnaireViewSet(ModelViewSet):
    serializer_class = DailyQuestionnaireSerializer

    def get_queryset(self):
        skin_care_prefetch = Prefetch(
            "tags_for_skin_care",
            queryset=UserTag.objects.filter(
                Q(user=self.request.user, category=TagCategories.SKIN_CARE)
                | Q(user=None, category=TagCategories.SKIN_CARE)
            ),
            to_attr="skin_care_tags",
        )
        well_being_prefetch = Prefetch(
            "tags_for_well_being",
            queryset=UserTag.objects.filter(
                Q(user=self.request.user, category=TagCategories.WELL_BEING)
                | Q(user=None, category=TagCategories.WELL_BEING)
            ),
            to_attr="well_being_tags",
        )
        nutrition_prefetch = Prefetch(
            "tags_for_nutrition",
            queryset=UserTag.objects.filter(
                Q(user=self.request.user, category=TagCategories.NUTRITION)
                | Q(user=None, category=TagCategories.NUTRITION)
            ),
            to_attr="nutrition_tags",
        )
        return DailyQuestionnaire.objects.prefetch_related(
            skin_care_prefetch, well_being_prefetch, nutrition_prefetch
        ).filter(user=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(methods=["get"], detail=False, url_path="latest-questionnaire")
    def latest_questionnaire(self, request, *args, **kwargs):
        latest_questionnaire = self.get_queryset().filter(created_at__date=timezone.now().date()).first()
        if not latest_questionnaire:
            raise exceptions.NotFound
        return Response(self.get_serializer(latest_questionnaire).data)


class DailyProductGroupViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet):
    serializer_class = DailyProductGroupSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return DailyProductGroup.objects.filter(user=self.request.user).prefetch_related(
            Prefetch("products", queryset=DailyProduct.objects.order_by("created_at"))
        )

    def perform_create(self, serializer):
        types = []
        for product in serializer.validated_data.get("products", []):
            if product_type := product.get("type"):
                if product_type not in types:
                    types.append(product_type)
                else:
                    raise ValidationError(Errors.DUPLICATE_PRODUCT_TYPE.value)
        super().perform_create(serializer)

    def list(self, request, *args, **kwargs):  # noqa: A003
        product_group = get_object_or_404(self.get_queryset())
        serializer = self.get_serializer(product_group)
        return Response(serializer.data)


class DailyProductViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = DailyProductSerializer

    def get_queryset(self):
        return DailyProduct.objects.filter(group__user=self.request.user).order_by("created_at")


class DailyProductCreateViewSet(mixins.CreateModelMixin, GenericViewSet):
    serializer_class = DailyProductCreateSerializer


class DailyProductBrandAutocompleteView(DailyProductAutocompleteMixin, autocomplete.Select2ListView):
    field = "brand"


class DailyProductNameAutocompleteView(DailyProductAutocompleteMixin, autocomplete.Select2ListView):
    field = "name"


class DailyProductIngredientsAutocompleteView(DailyProductAutocompleteMixin, autocomplete.Select2GroupListView):
    field = "ingredients"

    def __init__(self, **kwargs: dict) -> None:
        super().__init__(**kwargs)
        self._orginal_q = ""

    @no_type_check
    def get_list(self) -> list:
        templates = DailyProductTemplate.objects.annotate(label=Concat("brand", Value(" - "), "name")).order_by(
            "brand", "name"
        )
        if self.q:
            templates = templates.filter(label__icontains=self.q)
            self._orginal_q = self.q
            self.q = ""
        products = {}
        for template in templates:
            if template.label not in products:
                products[template.label] = []
            if template.ingredients not in products[template.label]:
                products[template.label].append(template.ingredients)
        return [""] + list(products.items())

    def get(self, request: Request, *args: list, **kwargs: dict) -> JsonResponse:
        if error := self._check_permissions():
            return error
        response = super().get(request, *args, **kwargs)  # type: ignore
        data = json.loads(response.content)
        if self._orginal_q:
            data["results"].append(
                {
                    "id": self._orginal_q,
                    "text": f'Create "{self._orginal_q}"',
                    "create_id": True,
                }
            )
        return JsonResponse(data)

    def get_item_as_group(self, entry: tuple) -> tuple:
        result = super().get_item_as_group(entry)
        if not result[0][0]:
            return ()
        return result


class RecommendationViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = RecommendationSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[Recommendation]:
        return Recommendation.objects.filter(user=self.request.user)

    def patch(self, request: Request) -> Response:
        serializers_list = []
        errors = []
        response_data = []
        featured_recommendations: list[bool] = []
        for data in request.data:
            instance = get_object_or_404(self.get_queryset(), id=data.pop("id", None))
            serializer = self.get_serializer(instance, data=data, partial=True)
            if serializer.is_valid():
                serializers_list.append(serializer)
            else:
                errors.append(serializer.errors)
            featured_recommendations = self._validate_duplicate_field(
                serializer.validated_data.get("is_featured"),
                featured_recommendations,
                Errors.MULTIPLE_FEATURED_RECOMMENDATIONS,
            )

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        for serializer in serializers_list:
            serializer.save()
            response_data.append(serializer.data)

        return Response(response_data)

    def _validate_duplicate_field(
        self, field: Union[bool, str, None], occurrences: list, error_message: Errors
    ) -> list:
        if field:
            if field in occurrences:
                raise ValidationError(error_message.value)
            else:
                occurrences.append(field)
        return occurrences

    def get_serializer(self, *args, **kwargs) -> RecommendationSerializer:
        if self.action == "create":
            kwargs["many"] = True
        return super().get_serializer(*args, **kwargs)

    def get_serializer_context(self) -> dict:
        context = super().get_serializer_context()
        context["availability"] = FaceScan.availability(self.request.user)
        return context

    def perform_create(self, serializer: RecommendationSerializer) -> None:
        featured_recommendations: list[bool] = []
        categories: list[str] = []
        for recommendation in serializer.validated_data:
            featured_recommendations = self._validate_duplicate_field(
                recommendation.get("is_featured"),
                featured_recommendations,
                Errors.MULTIPLE_FEATURED_RECOMMENDATIONS,
            )
            categories = self._validate_duplicate_field(
                recommendation.get("category"),
                categories,
                Errors.DUPLICATE_RECOMMENDATION_CATEGORIES,
            )
        serializer.save()


class FaceScanViewSet(ModelViewSet):
    serializer_class = FaceScanSerializer

    def get_queryset(self):
        return FaceScan.objects.filter(user=self.request.user)

    @action(methods=["get"], detail=False)
    def availability(self, request, *args, **kwargs):
        latest_face_scans = FaceScan.availability(self.request.user)
        return (
            Response(status=status.HTTP_400_BAD_REQUEST)
            if latest_face_scans
            else Response(status=status.HTTP_204_NO_CONTENT)
        )

    @action(methods=["get"], detail=False, url_path="latest-scan", url_name="latest-scan")
    def latest_scan(self, request, *args, **kwargs):
        latest_scan = None
        try:
            latest_scan_item = self.get_queryset().exclude(analytics__is_valid=False).latest("created_at")
            latest_scan = latest_scan_item.created_at
            is_processed = latest_scan_item.analytics is not None
        except FaceScan.DoesNotExist:
            is_processed = False
        except FaceScan.analytics.RelatedObjectDoesNotExist:
            is_processed = False
        return Response({"latest_scan": latest_scan, "is_processed": is_processed})

    @action(methods=["delete"], detail=False, url_path="bulk-delete", url_name="bulk-delete")
    def bulk_delete(self, request, *args, **kwargs):
        delete_ids = request.data.get("del_list")
        if not delete_ids:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        for identifier in delete_ids:
            get_object_or_404(FaceScan, pk=int(identifier)).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic
    @action(
        detail=False,
        methods=["post"],
        url_path="hautai/webhook",
        permission_classes=[AllowAny],
    )
    def webhook(self, request):
        is_valid = True
        if (
            request.query_params["auth_key"] == settings.HAUT_AI_AUTH_KEY
            and request.data["dataset_id"] == settings.HAUT_AI_DATA_SET_ID
        ):
            try:
                LOGGER.info(
                    "Received webhook from Haut.ai with image id %s",
                    request.data["image_id"],
                )
                face_scan = FaceScan.objects.get(haut_ai_image_id=request.data["image_id"])
                company_id, token = get_auth_info()

                smoothing_data = get_smoothing_results(
                    subject_id=face_scan.user.haut_ai_subject_id,
                    batch_id=face_scan.haut_ai_batch_id,
                    image_id=face_scan.haut_ai_image_id,
                    company_id=company_id,
                    token=token,
                )
                image_data = get_image_results(
                    subject_id=face_scan.user.haut_ai_subject_id,
                    batch_id=face_scan.haut_ai_batch_id,
                    image_id=face_scan.haut_ai_image_id,
                    company_id=company_id,
                    token=token,
                )
                site_config = SiteConfiguration.get_solo()
                device_pks = list(face_scan.user.fcmdevice_set.values_list("pk", flat=True))
                language_pk = face_scan.user.language.pk
                analytics_orm_data = build_orm_analytics_model(image_data)
                # For invalid face scan image data, analytics_orm_data is empty
                # That's why setting FaceScanAnalytic's is_valid=False and
                # sending push notification to the user to notify the problem.
                # And if the face scan is valid then notifying user that analysis
                # is completed.
                if not (analytics_orm_data and image_data[0]["is_ok"]):
                    is_valid = False
                    invalid_face_notification_template = site_config.invalid_face_scan_notification_template
                    if invalid_face_notification_template:
                        generate_and_send_notification.delay(
                            invalid_face_notification_template.pk,
                            FaceScanNotificationTypes.INVALID,
                            language_pk,
                            device_pks,
                        )
                    else:
                        LOGGER.error("No template found for invalid face scan notification.")
                else:
                    analysis_completed_notification_template = site_config.face_analysis_completed_notification_template
                    if analysis_completed_notification_template:
                        generate_and_send_notification.delay(
                            analysis_completed_notification_template.pk,
                            FaceScanNotificationTypes.SUCCESS,
                            language_pk,
                            device_pks,
                        )
                    else:
                        LOGGER.error("No template found for face analysis completed notification.")
                self._create_face_analytics_and_smoothing_results(
                    face_scan, analytics_orm_data, smoothing_data, image_data, is_valid
                )

            except FaceScan.DoesNotExist:
                LOGGER.error(
                    "Face scan with id %s not found for data analytics",
                    request.data["image_id"],
                )
        else:
            LOGGER.error(
                f"Invalid haut.ai parameters. "
                f"auth key is correct: {request.query_params['auth_key'] == settings.HAUT_AI_AUTH_KEY} "
                f"dataset is correct: {request.data['dataset_id'] == settings.HAUT_AI_DATA_SET_ID} "
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _create_face_analytics_and_smoothing_results(
        self,
        face_scan: FaceScan,
        analytics_orm_data: dict,
        smoothing_data: list,
        image_data: dict,
        is_valid: bool,
    ) -> None:
        if not FaceScanAnalytics.objects.filter(face_scan=face_scan).exists():
            FaceScanAnalytics.objects.create(
                **analytics_orm_data,
                face_scan=face_scan,
                raw_data=image_data,
                is_valid=is_valid,
            )
            FaceScanSmoothingAnalytics.objects.create(
                **build_orm_smoothing_analytics_model(smoothing_data),
                face_scan=face_scan,
                raw_data=smoothing_data,
            )


class FaceScanAnalyticsViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = FaceScanAnalyticsSerializer

    def get_queryset(self):
        return FaceScanAnalytics.objects.filter(face_scan__user=self.request.user, is_valid=True).prefetch_related(
            "face_scan"
        )


class FaceScanSmoothingAnalyticsViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = FaceScanSmoothingAnalyticsSerializer

    def get_queryset(self):
        return FaceScanSmoothingAnalytics.objects.filter(
            face_scan__user=self.request.user, face_scan__analytics__is_valid=True
        ).prefetch_related("face_scan")


class DailyStatisticsViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = StatisticsSerializer

    def get_queryset(self):
        return DailyStatistics.objects.filter(user=self.request.user)

    @extend_schema(**statistics_overview_schema)
    @action(methods=["get"], detail=False, url_path="overview", url_name="overview")
    def statistics_overview(self, request, *args, **kwargs):
        data = {}
        requested_date = None
        if date_str := request.query_params.get("date"):
            requested_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        today = requested_date or timezone.now()
        yesterday = today - datetime.timedelta(days=1)
        first_day_of_current_month = today.replace(day=1)
        last_day_of_previous_month = first_day_of_current_month - datetime.timedelta(days=1)

        statistics = self.get_queryset().annotate(daily_average=(F("skin_care") + F("well_being") + F("nutrition")) / 3)

        current_month_avg = statistics.filter(date__month=first_day_of_current_month.month).aggregate(
            current_month_average=Coalesce(Avg("daily_average", output_field=IntegerField()), 0)
        )
        data.update(current_month_avg)

        last_month_avg = statistics.filter(date__month=last_day_of_previous_month.month).aggregate(
            last_month_average=Coalesce(Avg("daily_average", output_field=IntegerField()), 0)
        )
        data.update(last_month_avg)

        today_avg = statistics.filter(date=today.date()).aggregate(
            today_average=Coalesce(Avg("daily_average", output_field=IntegerField()), 0)
        )
        data.update(today_avg)

        yesterday_avg = statistics.filter(date=yesterday.date()).aggregate(
            yesterday_average=Coalesce(Avg("daily_average", output_field=IntegerField()), 0)
        )
        data.update(yesterday_avg)
        return Response(data)


class FaceScanCommentViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = FaceScanCommentSerializer

    def get_queryset(self):
        user = self.request.user
        language_code = user.language.code if user.is_authenticated else settings.DEFAULT_LANGUAGE
        return FaceScanComment.objects.filter(face_scan__user=self.request.user).annotate(
            comment_message=Subquery(
                FaceScanCommentTemplateTranslation.objects.filter(
                    template=OuterRef("comment_template"), language=language_code
                ).values("body")[:1]
            )
        )


class PredictionViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = PredictionSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        available_translations = PredictionTemplateTranslation.objects.filter(language=self.get_user_language_code())
        translation_map = {
            translation.id: {
                "prediction": translation.body,
                "image": translation.image.url if translation.image else None,
                "title": translation.title,
            }
            for translation in available_translations
        }
        context["user_translations"] = translation_map
        return context

    def get_user_language_code(self) -> str:
        user = self.request.user
        language_code = user.language.code if user.is_authenticated else settings.DEFAULT_LANGUAGE
        return language_code

    def get_queryset(self):
        user = self.request.user
        prediction_translation = PredictionTemplateTranslation.objects.filter(
            template__name=OuterRef("prediction_type"),
            language=self.get_user_language_code(),
        )
        return Prediction.objects.filter(user=user).annotate(
            trans_template_id=Subquery(prediction_translation.values("id")[:1])
        )


class TagViewSet(ModelViewSet):
    serializer_class = UserTagSerializer
    filterset_fields = ["category", "name"]

    def get_queryset(self):
        filters = Q(user=self.request.user) | Q(user=None)
        if self.action in [
            "destroy",
            "partial_update",
            "update",
        ]:
            filters = Q(user=self.request.user)
        return self.serializer_class.Meta.model.objects.filter(filters)


class MedicationEventViewSet(ModelViewSet):
    serializer_class = MedicationEventSerializer

    def get_queryset(self):
        tag_prefetch = Prefetch(
            "event_tags",
            queryset=UserTag.objects.filter(
                Q(user=self.request.user, category=TagCategories.MEDICATION)
                | Q(user=None, category=TagCategories.MEDICATION)
            ),
            to_attr="medication_tags",
        )
        return self.serializer_class.Meta.model.objects.prefetch_related(tag_prefetch).filter(
            user=self.request.user, event_type=HealthCareEventTypes.MEDICATION
        )


class AppointmentEventViewSet(ModelViewSet):
    serializer_class = AppointmentEventSerializer

    def get_queryset(self):
        tag_prefetch = Prefetch(
            "event_tags",
            queryset=UserTag.objects.filter(
                Q(user=self.request.user, category=TagCategories.APPOINTMENT)
                | Q(user=None, category=TagCategories.APPOINTMENT)
            ),
            to_attr="appointment_tags",
        )
        return self.serializer_class.Meta.model.objects.prefetch_related(tag_prefetch).filter(
            user=self.request.user, event_type=HealthCareEventTypes.APPOINTMENT
        )


class MenstruationEventViewSet(ModelViewSet):
    serializer_class = MenstruationEventSerializer

    def get_queryset(self):
        tag_prefetch = Prefetch(
            "event_tags",
            queryset=UserTag.objects.filter(
                Q(user=self.request.user, category=TagCategories.MENSTRUATION)
                | Q(user=None, category=TagCategories.MENSTRUATION)
            ),
            to_attr="menstruation_tags",
        )
        return self.serializer_class.Meta.model.objects.prefetch_related(tag_prefetch).filter(
            user=self.request.user, event_type=HealthCareEventTypes.MENSTRUATION
        )


class ProgressViewSet(GenericViewSet):
    serializer_class = DailyQuestionnaireSerializer

    def get_start_and_end_date(self) -> tuple[datetime.date, datetime.date]:
        requested_month = None
        current_time = timezone.now()
        if month_str := self.request.query_params.get("month"):
            requested_month = datetime.datetime.strptime(month_str, "%Y-%m")
            if requested_month.month > current_time.month and requested_month.year >= current_time.year:
                raise ValidationError([Errors.FUTURE_MONTH_SELECTED_FOR_MONTHLY_PROGRESS.value])
        start_date = (requested_month or current_time.replace(day=1)).date()
        days_in_month = calendar.monthrange(start_date.year, start_date.month)[1]
        end_date = start_date + datetime.timedelta(days=days_in_month - 1)
        return start_date, end_date

    @extend_schema(**monthly_progress_schema)
    @action(methods=["get"], detail=False, url_path="monthly", url_name="monthly")
    def monthly_progress(self, request):
        return Response(generate_monthly_progress(*self.get_start_and_end_date(), self.request.user))


class StatisticsPurchaseViewSet(ReadOnlyModelViewSet):
    serializer_class = StatisticsPurchaseSerializer

    def get_queryset(self):
        return StatisticsPurchase.objects.filter(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="start")
    def start_purchase(self, request):
        LOGGER.info("Starting statistics purchase for user [%s].", self.request.user)
        started_purchase = StatisticsPurchase.objects.filter(
            user=self.request.user,
            store_product=request.data["store_product"],
            status=PurchaseStatus.STARTED.value,
        ).first()
        if started_purchase:
            serializer = StatisticsPurchaseSerializer(started_purchase)
            LOGGER.debug(
                "An already started statistics purchase has been found for user [%s] product [%s].",
                self.request.user,
                request.data["store_product"],
            )
            return Response(serializer.data, status.HTTP_200_OK)
        serializer = StatisticsPurchaseSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        serializer.save()
        LOGGER.debug(
            "Statistics purchase has been started successfully for user [%s].",
            self.request.user,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_purchase(self, request, pk=None):
        LOGGER.info(
            "Starting statistics purchase [%s] cancellation for user [%s].",
            pk,
            self.request.user,
        )
        instance = self.get_object()
        request_metadata = {
            "status": PurchaseStatus.CANCELED.value,
            "store_product": instance.store_product_id,
        }
        request.data.update(request_metadata)
        serializer = StatisticsPurchaseSerializer(
            instance=instance, data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        LOGGER.debug(
            "Statistics purchase [%s] has been cancelled successfully for user [%s].",
            pk,
            self.request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete_purchase(self, request, pk=None):
        LOGGER.info(
            "Starting statistics purchase [%s] completion for user [%s].",
            pk,
            self.request.user,
        )
        instance = self.get_object()
        request_metadata = {
            "status": PurchaseStatus.COMPLETED.value,
            "store_product": instance.store_product_id,
        }
        request.data.update(request_metadata)
        setattr(request, "action", "complete")  # noqa: B010
        serializer = StatisticsPurchaseSerializer(
            instance=instance, data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        LOGGER.debug(
            "Statistics purchase [%s] has been completed successfully for user [%s].",
            pk,
            self.request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["post"],
        url_path="play-store/webhook",
        permission_classes=[AllowAny],
    )
    def play_store_webhook(self, request):
        LOGGER.info("Received statistics subscription purchase notification from google play store.")
        if encoded_message := request.data.get("message", {}).get("data"):
            if notification_data := decode_data(encoded_message):
                LOGGER.info(
                    "Processing statistics subscription purchase notification message [%s].",
                    request.data.get("message", {}).get("message_id"),
                )
                process_statistics_purchase_play_store_notifications(notification_data)
        else:
            LOGGER.error("Invalid google play statistics subscription purchase notification.")
        return Response(status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="app-store/webhook",
        permission_classes=[AllowAny],
    )
    def apps_store_webhook(self, request):
        LOGGER.info("Received statistics subscription purchase notification from appstore.")
        if signed_payload := request.data.get("signedPayload"):
            notification_data = generate_unified_receipt(parse_jwt(signed_payload))
            notification_type = notification_data.get("notificationType")
            if notification_type and notification_data:
                process_statistics_purchase_app_store_notification(notification_type, notification_data)
            else:
                LOGGER.error("Invalid appstore statistics subscription purchase notification.")
        else:
            LOGGER.error("No signed payload found in appstore statistics subscription purchase notification.")
        return Response(status=status.HTTP_200_OK)


class ImportScrappedProductsView(APIView):
    @extend_schema(responses=ImportScrappedProductsSerializer)
    def post(self, request):
        if not request.user.is_superuser:
            return Response({"error": "you are not superuser"}, status=400)
        serializer = ImportScrappedProductsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        import_products_from_amazon.delay(
            amazon_url=serializer.validated_data["amazon_url"],
            pages=serializer.validated_data["pages"],
        )
        return Response({"message": "done"})


class DailyProductSetReview(APIView):
    @extend_schema(responses=DailyProductSetReviewSerializer)
    def post(self, request):
        serializer = DailyProductSetReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(validated_data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class ScrappedProductsStatistics(APIView):
    def get(self, request):
        if not request.user.is_superuser:
            return Response({"error": "you are not superuser"})
        queryset = DailyProduct.objects.values("id", "name", "image", "product_info")
        statistic = self.count_statistic(queryset)
        return Response({"statistic": statistic})

    def count_statistic(self, queryset):
        statistics = {
            "all_products": len(queryset),
            "with_photo": 0,
            "with_title": 0,
            "with_scrapped_product": 0,
        }
        for product in queryset:
            if product["image"]:
                statistics["with_photo"] += 1
            if product["name"]:
                statistics["with_title"] += 1
            if product["product_info"]:
                statistics["with_scrapped_product"] += 1
        return statistics


class ScrapedProductsViewSet(ReadOnlyModelViewSet):
    serializer_class = ScrappedProductSerializer
    filter_backends = [DjangoFilterBackend]
    # filterset_fields = ["recommended_product", "type"]
    filterset_class = ScrapedProductFilter

    def get_queryset(self):
        user_products = Prefetch(
            lookup="products",
            queryset=UserScrapedProduct.objects.filter(user=self.request.user),
            to_attr="user_products",
        )
        return ScrapedProduct.objects.prefetch_related(user_products)

    @extend_schema(**want_have_schema)
    @action(
        detail=True,
        methods=["put"],
        url_path="add-have-and-want",
        url_name="add-have-and-want",
    )
    def set_want_it(self, request, *args, **kwargs):
        user = self.request.user
        instance = self.get_object()
        user_scraped_product, _created = UserScrapedProduct.objects.get_or_create(user=user, product=instance)
        if request.data.get("want") is not None:
            user_scraped_product.want = request.data.get("want")
        if request.data.get("have") is not None:
            user_scraped_product.have = request.data.get("have")
        user_scraped_product.save()
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class FaceScansStatistics(APIView):
    def get(self, request):
        if not request.user.is_superuser:
            return Response({"error": "you are not superuser"})
        queryset = FaceScan.objects.values("id", "updated_sagging")
        statistic = self.count_statistic(queryset)
        return Response({"statistic": statistic})

    def count_statistic(self, queryset):
        statistics = {"all_facescans": len(queryset), "updated": 0, "not_updated": 0}
        for product in queryset:
            if product["updated_sagging"]:
                statistics["updated"] += 1
            else:
                statistics["not_updated"] += 1
        return statistics
