import datetime
import logging

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import JSONField, Q, QuerySet, F, Value, TextField  # type: ignore
from django.db.models.expressions import Func
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.text import slugify
from import_export.resources import ModelResource
import textdistance

from apps.chat_gpt.interfaces import ChatGptRekognitionInterface
from apps.home.models import FaceScanCommentTemplate, SiteConfiguration
from apps.monetization.helpers import (
    get_play_store_response,
    validate_android_subscription_purchase_receipt,
    get_app_store_response,
    validate_ios_subscription_purchase_receipt,
)
from apps.monetization.models import StoreProduct
from apps.routines import (
    DietBalance,
    ExerciseHours,
    FeelingToday,
    LifeHappened,
    RoutineType,
    SkinFeel,
    SleepQuality,
    SomethingSpecial,
    StressLevel,
    DailyRoutineCountStatus,
    PredictionTypes,
    TagCategories,
    HealthCareEventTypes,
    MedicationTypes,
    PurchaseStatus,
    AppStores,
    ProductType,
    RecommendationCategory,
)
from apps.text_rekognition.script import TextRekognition
from apps.users.models import User
from apps.utils.error_codes import Errors
from apps.utils.models import BaseModel, UUIDBaseModel
from apps.utils.storage import restricted_file_storage

LOGGER = logging.getLogger("app")


class UserScrapedProduct(BaseModel):
    product = models.ForeignKey("ScrapedProduct", related_name="products", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="user_products", on_delete=models.CASCADE)
    want = models.BooleanField(default=False)
    have = models.BooleanField(default=False)


class Routine(BaseModel):
    user = models.ForeignKey(User, related_name="routines", on_delete=models.CASCADE)
    routine_type = models.CharField(
        max_length=30,
        choices=RoutineType.get_choices(),
    )


class MorningQuestionnaire(BaseModel):
    user = models.ForeignKey(User, related_name="morning_questionnaires", on_delete=models.CASCADE)
    feeling_today = models.CharField(
        max_length=30,
        choices=FeelingToday.get_choices(),
    )
    hours_of_sleep = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(14)],
    )
    sleep_quality = models.CharField(
        max_length=30,
        choices=SleepQuality.get_choices(),
    )
    something_special = models.CharField(max_length=30, choices=SomethingSpecial.get_choices(), blank=True, default="")


class EveningQuestionnaire(BaseModel):
    user = models.ForeignKey(User, related_name="evening_questionnaires", on_delete=models.CASCADE)
    skin_feel = models.CharField(
        max_length=30,
        choices=SkinFeel.get_choices(),
    )
    diet_today = models.CharField(
        max_length=30,
        choices=DietBalance.get_choices(),
    )
    water = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    life_happened = models.CharField(max_length=30, choices=LifeHappened.get_choices(), blank=True, default="")
    stress_levels = models.CharField(
        max_length=30,
        choices=StressLevel.get_choices(),
    )
    exercise_hours = models.CharField(max_length=30, choices=ExerciseHours.get_choices())


class DailyQuestionnaire(BaseModel):
    user = models.ForeignKey(User, related_name="daily_questionnaires", on_delete=models.CASCADE)
    skin_feel = models.CharField(
        max_length=30,
        choices=SkinFeel.get_choices(),
    )
    diet_today = models.CharField(
        max_length=30,
        choices=DietBalance.get_choices(),
    )
    water = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(3)])
    life_happened = ArrayField(
        models.CharField(max_length=30, choices=LifeHappened.get_choices()),
        size=10,
        default=list,
        blank=True,
    )
    stress_levels = models.CharField(
        max_length=30,
        choices=StressLevel.get_choices(),
    )
    exercise_hours = models.CharField(max_length=30, choices=ExerciseHours.get_choices())
    feeling_today = models.CharField(
        max_length=30,
        choices=FeelingToday.get_choices(),
    )
    hours_of_sleep = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(14)],
    )
    sleep_quality = models.CharField(
        max_length=30,
        choices=SleepQuality.get_choices(),
    )
    something_special = ArrayField(
        models.CharField(max_length=30, choices=SomethingSpecial.get_choices()),
        size=10,
        default=list,
        blank=True,
    )
    tags_for_skin_care = models.ManyToManyField(
        "UserTag",
        related_name="skincare_tags",
        limit_choices_to={"category": TagCategories.SKIN_CARE},
    )
    tags_for_well_being = models.ManyToManyField(
        "UserTag",
        related_name="wellbeing_tags",
        limit_choices_to={"category": TagCategories.WELL_BEING},
    )
    tags_for_nutrition = models.ManyToManyField(
        "UserTag",
        related_name="nutrition_tags",
        limit_choices_to={"category": TagCategories.NUTRITION},
    )

    def __str__(self):
        return f"Daily routine for {self.user} at {self.created_at}"

    @classmethod
    def export_resource_classes(cls) -> dict[str, tuple[str, ModelResource]]:
        from apps.routines.resources import DailyQuestionnaireResource

        return {
            "daily_questionnaires": (
                "daily questionnaire resources",
                DailyQuestionnaireResource,
            ),
        }

    class Meta:
        ordering = ["-created_at"]


class DailyProductGroup(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="product_group")
    country = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.id} for {self.user}"

    @property
    def completed(self):
        return not self.products.filter(
            Q(name__exact="") | Q(brand__exact="") | Q(ingredients__exact="") | Q(size__exact="")
        ).exists()


class ScrapedProduct(models.Model):
    brand = models.CharField(blank=True, max_length=255)
    title = models.CharField(max_length=255, unique=True)
    image = models.ImageField(upload_to="scraped_products", blank=True, default="")
    ingredients = models.TextField(blank=True)
    url = models.URLField(blank=True)
    job_id = models.CharField(max_length=255)
    status_code = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_medication = models.BooleanField(default=False)
    source = models.CharField(blank=True, max_length=255)
    users = models.ManyToManyField(User, through="UserScrapedProduct", related_name="products")
    recommended_product = models.BooleanField(default=False)
    side_effects = models.CharField(blank=True, max_length=255)
    positive_effects = models.CharField(blank=True, max_length=255)
    type = models.CharField(max_length=11, choices=ProductType.get_choices(), blank=True)  # noqa: A003, VNE003

    def __str__(self):
        return self.title


class DailyProduct(BaseModel):
    group = models.ForeignKey(DailyProductGroup, related_name="products", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products", blank=True, default="")
    name = models.TextField(blank=True)
    brand = models.CharField(blank=True, max_length=255)
    ingredients = models.TextField(blank=True)
    size = models.CharField(blank=True, max_length=30)
    type = models.CharField(max_length=11, choices=ProductType.get_choices())  # noqa: A003, VNE003
    is_medication = models.BooleanField(default=False)
    product_info = models.ForeignKey(ScrapedProduct, on_delete=models.SET_NULL, null=True, blank=True)
    image_parse_fail = models.IntegerField(null=True, blank=True, default=0)
    connect_scrapped_fail = models.IntegerField(null=True, blank=True, default=0)
    review_score = models.IntegerField(null=True, blank=True, default=0)
    brand_updated = models.BooleanField(default=False)
    satisfaction_score = models.IntegerField(null=True, blank=True, default=0)
    preference_score = models.IntegerField(null=True, blank=True, default=0)
    efficiency_score = models.IntegerField(null=True, blank=True, default=0)
    accessibility_score = models.IntegerField(null=True, blank=True, default=0)
    easy_to_use_score = models.IntegerField(null=True, blank=True)
    cost_score = models.IntegerField(null=True, blank=True, default=0)
    parsed_by_chat_gpt_data = JSONField(null=True, blank=True)

    CLEARABLE_FIELDS = ["brand", "ingredients", "size"]
    CLEARABLE_FOREIGN_KEYS = ["product_info"]

    def __str__(self):
        return f"{self.id} {self.type}"

    def __init__(self, *args: list, **kwargs: dict) -> None:
        super().__init__(*args, **kwargs)
        self._original_image = self.image

    def save(self, *args: list, **kwargs: dict) -> None:  # type: ignore[override]
        if self.image != self._original_image:
            for field in self.CLEARABLE_FIELDS:
                setattr(self, field, "")
                self.product_info = None
            super().save(*args, **kwargs)  # type: ignore[arg-type]
            self.name = self.save_name_from_parsed_image()
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    # def create

    def save_name_from_parsed_image(self):
        try:
            img_file = self.image
        except ValueError:
            self.add_image_parse_fail_count()
            return ""
        result = TextRekognition.run_bytes(img_file)
        if result == "":
            self.add_image_parse_fail_count()
            self.image = None
        else:
            self.remove_image_parse_fail_count()
            self.parsed_by_chat_gpt_data = ChatGptRekognitionInterface.parse_rekognition_text(result)
            if self.parsed_by_chat_gpt_data:
                self.brand = self.parsed_by_chat_gpt_data.get("brand")
        return result

    def add_image_parse_fail_count(self):
        self.image_parse_fail += 1

    def remove_image_parse_fail_count(self):
        self.image_parse_fail = 0

    def get_similar_scrapped_product_by_title(self, lens_title):
        formatted_title = Func(
            F("lower_title"),
            Value(" "),
            function="regexp_split_to_array",
            output=ArrayField(TextField()),
        )
        tokens_list = self.lens_title_to_tokens_list(lens_title)
        scrapped_products = (
            ScrapedProduct.objects.annotate(lower_title=Lower("title"))
            .annotate(formatted_title=formatted_title)
            .filter(formatted_title__contains=tokens_list[0])
            .values("id", "brand", "title", "ingredients", "formatted_title")
        )
        if not scrapped_products:
            return None
        scrapped_products = self.calculate_jaccard_distance(scrapped_products, tokens_list)
        return self.get_product_with_biggest_jaccard_distance(scrapped_products)

    @staticmethod
    def lens_title_to_tokens_list(lens_title: str):
        lens_title = lens_title.lower()
        for symbol in [
            "~",
            ":",
            "'",
            "+",
            "[",
            "\\",
            "@",
            "^",
            "{",
            "%",
            "(",
            "-",
            '"',
            "*",
            "|",
            ",",
            "&",
            "<",
            "`",
            "}",
            ".",
            "_",
            "=",
            "]",
            "!",
            ">",
            ";",
            "?",
            "#",
            "$",
            ")",
            "/",
        ]:
            lens_title = lens_title.replace(symbol, "")
        return lens_title.split(" ")

    @staticmethod
    def calculate_jaccard_distance(scrapped_products, tokens_list):
        for product in scrapped_products:
            product["jaccard_distance"] = textdistance.jaccard(product.get("formatted_title"), tokens_list)
        return sorted(scrapped_products, key=lambda k: k["jaccard_distance"], reverse=True)

    @staticmethod
    def get_product_with_biggest_jaccard_distance(products):
        try:
            if products[0].get("jaccard_distance") < 0.4:
                return None
            else:
                return ScrapedProduct.objects.get(id=products[0].get("id"))
        except (IndexError, ScrapedProduct.DoesNotExist):
            return None

    @property
    def completed(self):
        return all([self.name, self.brand, self.ingredients, self.size])

    @classmethod
    def get_field_values(cls, field: str) -> set[str]:
        return set(cls.objects.values_list(field, flat=True))


class DailyProductTemplate(BaseModel):
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255)
    ingredients = models.TextField()

    def __str__(self) -> str:
        return f"{self.brand} {self.name}"


class FaceScan(BaseModel):
    user = models.ForeignKey(User, related_name="face_scans", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="face_scan", storage=restricted_file_storage)
    haut_ai_batch_id = models.CharField(blank=True, max_length=250)
    haut_ai_image_id = models.CharField(blank=True, max_length=250)
    updated_sagging = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} face scan {self.created_at}"

    @classmethod
    def availability(cls, user: User) -> bool:
        queryset = cls.objects.filter(user=user)

        current_time = timezone.now()
        user_is_premium = StatisticsPurchase.objects.filter(
            status__in=[PurchaseStatus.COMPLETED.value, PurchaseStatus.EXPIRED.value],
            purchase_started_on__lt=current_time,
            purchase_ends_after__gt=current_time,
            user=user,
        ).exists()
        if user_is_premium:
            latest_face_scans = queryset.filter(created_at__date=current_time.date(), analytics__is_valid=True).exists()
        else:
            siteconfig = SiteConfiguration.get_solo()
            latest_face_scans = queryset.filter(
                created_at__date__gte=current_time.date() - datetime.timedelta(days=siteconfig.scan_duration - 1),
                analytics__is_valid=True,
            ).exists()
        return latest_face_scans

    @classmethod
    def export_resource_classes(cls) -> dict[str, tuple[str, ModelResource]]:
        from apps.routines.resources import FaceScanResource

        return {
            "face_scans": ("face scan resources", FaceScanResource),
        }


class FaceScanAnalytics(BaseModel):
    face_scan = models.OneToOneField(FaceScan, related_name="analytics", on_delete=models.CASCADE)
    acne = models.PositiveIntegerField(default=0)
    lines = models.PositiveIntegerField(default=0)
    wrinkles = models.PositiveIntegerField(default=0)
    pigmentation = models.PositiveIntegerField(default=0)
    translucency = models.PositiveIntegerField(default=0)
    quality = models.PositiveIntegerField(default=0)
    eye_bags = models.PositiveIntegerField(default=0)
    pores = models.PositiveIntegerField(default=0)
    sagging = models.PositiveIntegerField(default=0)
    uniformness = models.PositiveIntegerField(default=0)
    hydration = models.PositiveIntegerField(default=0)
    redness = models.PositiveIntegerField(default=0)
    is_valid = models.BooleanField(default=True)
    raw_data = JSONField()

    def __str__(self):
        return f"{self.face_scan.user} face scan analytics {self.created_at}"

    class Meta:
        ordering = ["-created_at"]


class Recommendation(BaseModel):
    user = models.ForeignKey(User, related_name="recommendations", on_delete=models.CASCADE)
    category = models.CharField(max_length=12, choices=RecommendationCategory.get_choices())
    previuos_indexes = ArrayField(models.PositiveIntegerField(), default=list, blank=True)
    current_index = models.PositiveIntegerField(null=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "category"], name="One category per user")]

    def __str__(self) -> str:
        return f"{self.category} recommendation for {self.user}"


class FaceScanSmoothingAnalytics(BaseModel):
    face_scan = models.OneToOneField(FaceScan, related_name="smoothing_analytics", on_delete=models.CASCADE)
    acne = models.PositiveIntegerField(default=0)
    lines = models.PositiveIntegerField(default=0)
    wrinkles = models.PositiveIntegerField(default=0)
    pigmentation = models.PositiveIntegerField(default=0)
    translucency = models.PositiveIntegerField(default=0)
    quality = models.PositiveIntegerField(default=0)
    eye_bags = models.PositiveIntegerField(default=0)
    pores = models.PositiveIntegerField(default=0)
    sagging = models.PositiveIntegerField(default=0)
    uniformness = models.PositiveIntegerField(default=0)
    hydration = models.PositiveIntegerField(default=0)
    redness = models.PositiveIntegerField(default=0)
    raw_data = JSONField()

    def __str__(self):
        return f"{self.face_scan.user} face scan smoothing analytics {self.created_at}"

    class Meta:
        ordering = ["-created_at"]


class DailyStatistics(BaseModel):
    user = models.ForeignKey(User, related_name="daily_statistics", on_delete=models.CASCADE)
    skin_care = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(100)],
        default=0,
        help_text="skin care points in percentage",
    )
    well_being = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(100)],
        default=0,
        help_text="well being points in percentage",
    )
    nutrition = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(100)],
        default=0,
        help_text="nutrition points in percentage",
    )
    routine_count_status = models.CharField(max_length=30, choices=DailyRoutineCountStatus.get_choices())
    date = models.DateField(help_text="date for the statistics")

    def __str__(self):
        return f"{self.user} daily statistics for {self.date}"

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "date"], name="One statistics per day")]
        ordering = ["-date"]


class FaceScanComment(BaseModel):
    face_scan = models.OneToOneField(FaceScan, related_name="face_scan_comments", on_delete=models.CASCADE)
    comment_template = models.ForeignKey(
        FaceScanCommentTemplate,
        related_name="face_scan_comment_templates",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"comment for face scan {self.face_scan.id} at {self.created_at}"


class Prediction(BaseModel):
    user = models.ForeignKey(User, related_name="predictions", on_delete=models.CASCADE)
    prediction_type = models.CharField(
        max_length=100,
        choices=PredictionTypes.get_choices(),
    )
    date = models.DateField(help_text="date for the prediction")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "date"], name="One prediction per day")]
        ordering = ["-date"]


class UserTag(BaseModel):
    name = models.CharField(help_text="tag name.", max_length=100)
    slug = models.SlugField(editable=False, max_length=128)
    user = models.ForeignKey(User, related_name="tags", on_delete=models.CASCADE, null=True, blank=True)
    category = models.CharField(max_length=30, choices=TagCategories.get_choices())

    def __str__(self):
        return f"{self.name}"

    def _check_tag_name_exists(self) -> None:
        slug_name = slugify(self.name)
        other_tags_with_same_name = UserTag.objects.filter(
            slug=slug_name, user=self.user, category=self.category
        ).exclude(id=self.id)
        if other_tags_with_same_name.count() > 0:
            raise ValidationError({"name": Errors.TAG_NAME_ALREADY_EXISTS_FOR_SAME_CATEGORY.value})

    def clean(self):
        super().clean()
        self._check_tag_name_exists()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "slug", "category"],
                name="One tag per user per category",
            ),
            models.UniqueConstraint(
                fields=["slug", "category"],
                condition=Q(user__isnull=True),
                name="One predefined tag per category",
            ),
        ]
        ordering = ["-created_at"]


class HealthCareEvent(BaseModel):
    user = models.ForeignKey(User, related_name="health_care_events", on_delete=models.CASCADE)
    name = models.CharField(max_length=300, blank=True, default="")
    event_type = models.CharField(max_length=100, choices=HealthCareEventTypes.get_choices())
    medication_type = models.CharField(max_length=30, choices=MedicationTypes.get_choices(), blank=True, default="")
    start_date = models.DateField(help_text="start date for the event")
    duration = models.PositiveSmallIntegerField(help_text="event duration in days", null=True, blank=True)
    time = models.TimeField(help_text="time for the event", null=True, blank=True)
    event_tags = models.ManyToManyField(
        "UserTag",
        related_name="health_care_event_tags",
        limit_choices_to={
            "category__in": [
                TagCategories.MEDICATION,
                TagCategories.APPOINTMENT,
                TagCategories.MENSTRUATION,
            ]
        },
    )
    remind_me = models.BooleanField(default=True)
    is_reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(help_text="reminder sent at", null=True, blank=True)

    def _check_appointment_already_exists_on_same_datetime(self) -> None:
        filters = Q(
            start_date=self.start_date,
            time=self.time,
            event_type=HealthCareEventTypes.APPOINTMENT,
        )
        filters &= ~Q(id=self.id)
        if self.__class__.objects.filter(filters).count() > 0:
            raise ValidationError([Errors.APPOINTMENT_EVENT_ALREADY_EXISTS_FOR_SAME_DATE_TIME.value])

    def _validate_medication_event(self) -> None:
        if not all([self.name, self.medication_type, self.duration]):
            raise ValidationError([Errors.INVALID_MEDICATION_EVENT.value])

    def _validate_appointment_event(self) -> None:
        if not all([self.name, self.time]):
            raise ValidationError([Errors.INVALID_APPOINTMENT_EVENT.value])
        self._check_appointment_already_exists_on_same_datetime()

    def _validate_menstruation_event(self) -> None:
        if self.duration is None:
            raise ValidationError([Errors.INVALID_MENSTRUATION_EVENT.value])

    def clean(self):
        super().clean()
        if self.event_type == HealthCareEventTypes.MEDICATION:
            self._validate_medication_event()
        elif self.event_type == HealthCareEventTypes.APPOINTMENT:
            self._validate_appointment_event()
        elif self.event_type == HealthCareEventTypes.MENSTRUATION:
            self._validate_menstruation_event()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(
                        event_type=HealthCareEventTypes.MEDICATION,
                        time__isnull=True,
                        duration__isnull=False,
                    )
                    & (~Q(medication_type="") & ~Q(name=""))
                )
                | (
                    Q(
                        event_type=HealthCareEventTypes.MENSTRUATION,
                        medication_type="",
                        name="",
                        duration__isnull=False,
                        time__isnull=True,
                    )
                )
                | (
                    Q(
                        event_type=HealthCareEventTypes.APPOINTMENT,
                        duration__isnull=True,
                        medication_type="",
                        time__isnull=False,
                    )
                    & ~Q(name="")
                ),
                name="check valid event",
            ),
        ]
        ordering = ["-start_date"]


class StatisticsPurchase(UUIDBaseModel):
    user = models.ForeignKey(User, related_name="purchased_statistics", on_delete=models.CASCADE)
    store_product = models.ForeignKey(StoreProduct, related_name="purchases", on_delete=models.PROTECT)
    store_name = models.CharField(
        choices=AppStores.get_choices(),
        default=AppStores.APP_STORE.value,
        max_length=100,
    )
    receipt_data = models.TextField(blank=True, default="", help_text="Appstore receipt data")
    transaction_id = models.CharField(
        help_text="subscription purchase order or transaction id",
        blank=True,
        default="",
        max_length=200,
    )
    purchase_started_on = models.DateTimeField(help_text="purchase started on date time", null=True, blank=True)
    purchase_ends_after = models.DateTimeField(help_text="purchase ends after date time", null=True, blank=True)
    total_transactions = models.PositiveSmallIntegerField(
        help_text="total subscription transactions", default=0, blank=True
    )
    status = models.CharField(
        choices=PurchaseStatus.get_choices(),
        default=PurchaseStatus.STARTED.value,
        max_length=100,
    )

    def _check_subscription_already_purchased(self) -> None:
        if StatisticsPurchase.objects.filter(
            user=self.user,
            store_product=self.store_product,
            status=PurchaseStatus.COMPLETED.value,
        ).exists():
            raise ValidationError([Errors.USER_ALREADY_PURCHASED_STATISTICS.value])

    def _has_subscription_purchase_started(self) -> QuerySet["StatisticsPurchase"]:
        return StatisticsPurchase.objects.filter(
            user=self.user,
            store_product=self.store_product,
            status=PurchaseStatus.STARTED.value,
        )

    def _validate_subscription_purchase_cancellation(self) -> None:
        if not self._has_subscription_purchase_started().filter(id=self.id).exists():
            raise ValidationError([Errors.INVALID_STATISTICS_PURCHASE_TO_CANCEL.value])

    def _validate_subscription_purchase_completion(self) -> None:
        if not self._has_subscription_purchase_started().filter(id=self.id).exists():
            raise ValidationError([Errors.INVALID_STATISTICS_PURCHASE_TO_COMPLETE.value])
        self._check_purchase_receipt_validity()

    def _check_purchase_receipt_validity(self) -> None:
        if self.store_name == AppStores.APP_STORE.value:
            appstore_response = get_app_store_response(
                {
                    "receipt-data": self.receipt_data,
                    "password": settings.APPLE_SHARED_APP_SECRET,
                    "exclude-old-transactions": True,
                }
            )
            (
                app_account_token,
                self.transaction_id,
                self.purchase_started_on,
                self.purchase_ends_after,
            ) = validate_ios_subscription_purchase_receipt(appstore_response)
            self._check_token_authenticity(app_account_token)
            self.total_transactions += 1

        elif self.store_name == AppStores.PLAY_STORE.value:
            play_store_response = get_play_store_response(
                {
                    "packageName": settings.PLAY_STORE_PACKAGE_NAME,
                    "subscriptionId": self.store_product.sku,
                    "token": self.receipt_data,
                }
            )
            (
                obfuscated_account_id,
                self.transaction_id,
                self.purchase_started_on,
                self.purchase_ends_after,
            ) = validate_android_subscription_purchase_receipt(play_store_response)
            self._check_token_authenticity(obfuscated_account_id)
            self.total_transactions += 1

    def _check_token_authenticity(self, token: str) -> None:
        if token != str(self.id):
            existing_purchase = StatisticsPurchase.objects.filter(
                ~Q(status=PurchaseStatus.COMPLETED.value), user=self.user, id=token
            ).exists()
            if not existing_purchase:
                raise ValidationError([Errors.PURCHASE_TOKEN_BELONGS_TO_OTHER_USER.value])

    def save(self, *args, **kwargs):
        is_receipt_verified = kwargs.pop("is_verified", False)
        if self.status == PurchaseStatus.STARTED.value:
            self._check_subscription_already_purchased()
        elif self.status == PurchaseStatus.CANCELED.value:
            self._validate_subscription_purchase_cancellation()
        elif self.status == PurchaseStatus.COMPLETED.value:
            # Skipping receipt validation if it is already validated
            if not is_receipt_verified:
                self._validate_subscription_purchase_completion()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class PurchaseHistory(BaseModel):
    status = models.CharField(
        max_length=50,
        choices=PurchaseStatus.get_choices(),
        default=PurchaseStatus.STARTED.value,
    )
    purchase = models.ForeignKey("routines.StatisticsPurchase", on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Purchase History"
