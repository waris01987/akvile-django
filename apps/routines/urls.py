from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.routines.views import (
    FaceScanViewSet,
    RoutineViewSet,
    MorningQuestionnaireViewSet,
    EveningQuestionnaireViewSet,
    FaceScanAnalyticsViewSet,
    FaceScanSmoothingAnalyticsViewSet,
    DailyQuestionnaireViewSet,
    DailyStatisticsViewSet,
    FaceScanCommentViewSet,
    PredictionViewSet,
    TagViewSet,
    MedicationEventViewSet,
    AppointmentEventViewSet,
    MenstruationEventViewSet,
    ProgressViewSet,
    StatisticsPurchaseViewSet,
    DailyProductGroupViewSet,
    DailyProductViewSet,
    DailyProductBrandAutocompleteView,
    DailyProductNameAutocompleteView,
    DailyProductIngredientsAutocompleteView,
    RecommendationViewSet,
    ImportScrappedProductsView,
    ScrappedProductsStatistics,
    FaceScansStatistics,
    DailyProductSetReview,
    ScrapedProductsViewSet,
    DailyProductCreateViewSet,
)

router = DefaultRouter()
router.register("recommendations", RecommendationViewSet, basename="recommendations")
router.register("face-scans", FaceScanViewSet, basename="face_scans")
router.register("face-scan-analytics", FaceScanAnalyticsViewSet, basename="face_scan_analytics")
router.register(
    "face-scan-smoothing-analytics",
    FaceScanSmoothingAnalyticsViewSet,
    basename="face_scan_smoothing_analytics",
)
router.register("daily-product-groups", DailyProductGroupViewSet, basename="daily_product_groups")
router.register("daily-products", DailyProductViewSet, basename="daily_products")
router.register("daily-product-create", DailyProductCreateViewSet, basename="daily_product_create")
router.register("routines", RoutineViewSet, basename="routines")
router.register(
    "morning-questionnaires",
    MorningQuestionnaireViewSet,
    basename="morning_questionnaires",
)
router.register(
    "evening-questionnaires",
    EveningQuestionnaireViewSet,
    basename="evening_questionnaires",
)
router.register("daily-questionnaires", DailyQuestionnaireViewSet, basename="daily_questionnaires")
router.register("statistics", DailyStatisticsViewSet, basename="statistics")
router.register("face-scan-comments", FaceScanCommentViewSet, basename="face-scan-comments")
router.register("predictions", PredictionViewSet, basename="predictions")
router.register("tags", TagViewSet, basename="tags")
router.register("medication-events", MedicationEventViewSet, basename="medication-events")
router.register("appointment-events", AppointmentEventViewSet, basename="appointment-events")
router.register("menstruation-events", MenstruationEventViewSet, basename="menstruation-events")
router.register("progress", ProgressViewSet, basename="progress")
router.register("statistics-purchases", StatisticsPurchaseViewSet, basename="statistics-purchases")
router.register("scraped-products", ScrapedProductsViewSet, basename="scraped-products")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "daily-product-brand-autocomplete",
        DailyProductBrandAutocompleteView.as_view(),
        name="daily-product-brand-autocomplete",
    ),
    path(
        "daily-product-name-autocomplete",
        DailyProductNameAutocompleteView.as_view(),
        name="daily-product-name-autocomplete",
    ),
    path(
        "daily-product-ingredients-autocomplete",
        DailyProductIngredientsAutocompleteView.as_view(),
        name="daily-product-ingredients-autocomplete",
    ),
    path(
        "import-scrapped-products/",
        ImportScrappedProductsView.as_view(),
        name="import_scrapped_products",
    ),
    path(
        "daily-product-set-review/",
        DailyProductSetReview.as_view(),
        name="daily_product_review",
    ),
    path(
        "get-daily-products-statistics/",
        ScrappedProductsStatistics.as_view(),
        name="get_scrapped_products_statistics",
    ),
    path(
        "get-face-scans-statistics/",
        FaceScansStatistics.as_view(),
        name="get_face_scans_statistics",
    ),
]
