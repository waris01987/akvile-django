import copy
from typing import Optional

from django.core.exceptions import ValidationError as CoreValidationError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.routines import HealthCareEventTypes, ProductType
from apps.routines.models import (
    FaceScan,
    Routine,
    MorningQuestionnaire,
    EveningQuestionnaire,
    FaceScanSmoothingAnalytics,
    FaceScanAnalytics,
    DailyQuestionnaire,
    DailyStatistics,
    FaceScanComment,
    Prediction,
    UserTag,
    HealthCareEvent,
    StatisticsPurchase,
    PurchaseHistory,
    DailyProductGroup,
    DailyProduct,
    Recommendation,
    ScrapedProduct,
)
from apps.text_rekognition.script import TextRekognition
from apps.users.models import User
from apps.utils.error_codes import Errors


class RoutineSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Routine
        fields = ["user", "routine_type", "created_at"]


class MorningQuestionnaireSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = MorningQuestionnaire
        fields = [
            "user",
            "feeling_today",
            "hours_of_sleep",
            "sleep_quality",
            "something_special",
            "created_at",
        ]

    def validate(self, attrs):
        user = self.context["request"].user
        if "something_special" in attrs:
            if attrs["something_special"] == "SHAVING" and user.questionnaire.menstruating_person:
                raise ValidationError(Errors.MENSTRUATING_PERSON_DOES_NOT_HAVE_SHAVING_OPTION.value)
            if attrs["something_special"] == "MENSTRUATION" and not user.questionnaire.menstruating_person:
                raise ValidationError(Errors.NOT_MENSTRUATING_PERSON_WITH_MENSTRUATING_PERSONS_ANSWERS.value)
        return attrs


class EveningQuestionnaireSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    diet = serializers.SerializerMethodField()

    class Meta:
        model = EveningQuestionnaire
        fields = [
            "user",
            "skin_feel",
            "diet_today",
            "diet",
            "water",
            "life_happened",
            "stress_levels",
            "exercise_hours",
            "created_at",
        ]
        extra_kwargs = {
            "diet_today": {"required": False},
            "diet": {"required": False},
        }

    def validate(self, attrs):  # noqa C901
        if not attrs.get("diet_today"):
            attrs["diet_today"] = self.context["request"].data.get("diet", "")
        return attrs

    def get_diet(self, obj):
        return ""


class DailyQuestionnaireSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    skin_care_tags = serializers.SerializerMethodField()
    well_being_tags = serializers.SerializerMethodField()
    nutrition_tags = serializers.SerializerMethodField()
    diet = serializers.SerializerMethodField()

    class Meta:
        model = DailyQuestionnaire
        fields = [
            "user",
            "feeling_today",
            "hours_of_sleep",
            "sleep_quality",
            "something_special",
            "skin_feel",
            "diet_today",
            "diet",
            "water",
            "life_happened",
            "stress_levels",
            "exercise_hours",
            "skin_care_tags",
            "well_being_tags",
            "nutrition_tags",
            "tags_for_skin_care",
            "tags_for_well_being",
            "tags_for_nutrition",
            "created_at",
        ]
        extra_kwargs = {
            "tags_for_skin_care": {
                "allow_empty": True,
                "write_only": True,
                "required": False,
            },
            "tags_for_well_being": {
                "allow_empty": True,
                "write_only": True,
                "required": False,
            },
            "tags_for_nutrition": {
                "allow_empty": True,
                "write_only": True,
                "required": False,
            },
            "diet_today": {"required": False},
            "diet": {"required": False},
        }

    def validate(self, attrs):  # noqa C901
        user = self.context["request"].user
        if not getattr(user, "questionnaire", None):
            raise ValidationError(Errors.USER_HAS_NO_USER_QUESTIONNAIRE.value)
        if "something_special" in attrs:
            if "SHAVING" in attrs["something_special"] and user.questionnaire.menstruating_person:
                raise ValidationError(Errors.MENSTRUATING_PERSON_DOES_NOT_HAVE_SHAVING_OPTION.value)
            if "MENSTRUATION" in attrs["something_special"] and not user.questionnaire.menstruating_person:
                raise ValidationError(Errors.NOT_MENSTRUATING_PERSON_WITH_MENSTRUATING_PERSONS_ANSWERS.value)
        if "life_happened" in attrs:
            if "INNOCENT" in attrs["life_happened"] and len(attrs["life_happened"]) > 1:
                raise ValidationError(Errors.INNOCENT_PERSON_CAN_NOT_SELECT_MULTIPLE_LIFE_HAPPENED_ANSWERS.value)
        if not attrs.get("diet_today"):
            attrs["diet_today"] = self.context["request"].data.get("diet", "")
        return attrs

    def get_skin_care_tags(self, obj) -> list[str]:
        if hasattr(obj, "skin_care_tags"):
            return [item.name for item in obj.skin_care_tags]
        return obj.tags_for_skin_care.values_list("name", flat=True)

    def get_well_being_tags(self, obj) -> list[str]:
        if hasattr(obj, "well_being_tags"):
            return [item.name for item in obj.well_being_tags]
        return obj.tags_for_well_being.values_list("name", flat=True)

    def get_nutrition_tags(self, obj) -> list[str]:
        if hasattr(obj, "nutrition_tags"):
            return [item.name for item in obj.nutrition_tags]
        return obj.tags_for_nutrition.values_list("name", flat=True)

    def get_diet(self, obj):
        return ""


class ScrappedProductSerializer(serializers.ModelSerializer):
    want = serializers.SerializerMethodField()
    have = serializers.SerializerMethodField()

    def get_want(self, user):
        return user.user_products[0].want if user.user_products else False

    def get_have(self, user):
        return user.user_products[0].have if user.user_products else False

    class Meta:
        model = ScrapedProduct
        fields = [
            "id",
            "image",
            "title",
            "brand",
            "ingredients",
            "want",
            "have",
            "recommended_product",
            "side_effects",
            "positive_effects",
            "type",
        ]
        read_only_fields = [
            "id",
            "image",
            "title",
            "brand",
            "ingredients",
            "recommended_product",
            "side_effects",
            "positive_effects",
            "type",
        ]


class DailyProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyProduct
        fields = ["id", "name", "image", "brand", "ingredients", "size", "type"]
        extra_kwargs = {field: {"read_only": True} for field in DailyProduct.CLEARABLE_FIELDS}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields["type"].read_only = True

    def validate(self, data):
        data = super().validate(data)
        image = data.get("image")
        if not image:
            raise ValidationError({"image": Errors.NO_IMAGE_PROVIDED.value})
        return data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.product_info:
            representation["product_info"] = {
                "id": instance.product_info.id or None,
                "title": instance.product_info.title or None,
                "brand": instance.product_info.brand or None,
                "ingredients": instance.product_info.ingredients or None,
                "url": instance.product_info.url or None,
            }
        else:
            representation["product_info"] = {
                "id": None,
                "title": None,
                "brand": None,
                "ingredients": None,
                "url": None,
            }
        if instance.name:
            representation["image_parsing_success"] = True
        else:
            representation["image_parsing_success"] = False
        return representation


class DailyProductCreateSerializer(DailyProductSerializer):
    def validate(self, data):
        data = super().validate(data)
        try:
            user = self.context["request"].user
            data["group"] = user.product_group
        except User.product_group.RelatedObjectDoesNotExist:
            raise ValidationError(Errors.PRODUCT_GROUP_DOESNT_EXIST.value)
        if data.get("image"):
            name = TextRekognition.run_bytes(data.get("image"))
            if not name:
                data["image"] = None
            else:
                data["name"] = name
        return data


class DailyProductGroupSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    products = DailyProductSerializer(many=True)

    class Meta:
        model = DailyProductGroup
        fields = ["id", "user", "country", "products"]

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        if (request := self.context.get("request")) and getattr(request.user, "product_group", None):
            raise ValidationError(Errors.PRODUCT_GROUP_ALREADY_EXISTS.value)
        return attrs

    def create(self, validated_data):
        products = validated_data.pop("products", [])
        types = list(dict(ProductType.get_choices()).keys())
        for product in products:
            if product["type"] in types:
                types.remove(product["type"])
        all_products = sorted(
            products + [{"type": product_type} for product_type in types],
            key=lambda x: x["type"],
        )
        product_group = super().create(validated_data)
        for product in all_products:
            if product.get("image") and not TextRekognition.run_bytes(product.get("image")):
                product["image"] = None
        DailyProduct.objects.bulk_create([DailyProduct(group=product_group, **product) for product in all_products])
        return product_group


class FaceScanSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = FaceScan
        fields = [
            "user",
            "id",
            "image",
            "created_at",
        ]


class RecommendationSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Recommendation
        fields = [
            "id",
            "user",
            "category",
            "previuos_indexes",
            "current_index",
            "is_featured",
            "created_at",
            "updated_at",
        ]

    def __init__(self, *args: list, **kwargs: dict) -> None:
        super().__init__(*args, **kwargs)
        if not self.instance:
            self.fields["previuos_indexes"].read_only = True
        else:
            self.fields["category"].read_only = True
            self.fields["user"].read_only = True

    def update(self, instance: Recommendation, validated_data: dict) -> Recommendation:
        previuos_indexes = instance.previuos_indexes
        is_featured = instance.is_featured
        if instance.current_index and instance.current_index != validated_data.get("current_index"):
            previuos_indexes.append(instance.current_index)
        instance = super().update(instance, validated_data)
        if validated_data.get("is_featured") and not is_featured:
            Recommendation.objects.filter(user=instance.user).exclude(id=instance.id).update(is_featured=False)
        return instance

    def validate_previuos_indexes(self, previuos_indexes: list[int]) -> list[int]:
        if previuos_indexes != [] and (self.instance and previuos_indexes != self.instance.previuos_indexes):
            raise ValidationError(Errors.PREVIOUS_INDEXES_CAN_ONLY_BE_RESET.value)
        return previuos_indexes

    def validate(self, attrs: dict) -> dict:
        if not self.instance and Recommendation.objects.filter(user=attrs["user"], category=attrs["category"]).exists():
            raise ValidationError(Errors.USER_CAN_HAVE_ONE_RECOMMENDATION_PER_CATEGORY.value)
        if self.instance and attrs.get("current_index") in self.instance.previuos_indexes:
            raise ValidationError(Errors.CURRENT_INDEX_CANT_MATCH_PREVIOUS_INDEXES.value)
        return attrs

    def to_representation(self, instance: Recommendation) -> dict:
        representation = super().to_representation(instance)
        availability = (
            self.context["availability"] if "availability" in self.context else FaceScan.availability(instance.user)
        )
        if not availability:
            representation["previuos_indexes"].append(representation["current_index"])
            representation["current_index"] = None
        return representation


class FaceScanAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaceScanAnalytics
        fields = [
            "created_at",
            "acne",
            "lines",
            "wrinkles",
            "pigmentation",
            "translucency",
            "quality",
            "eye_bags",
            "pores",
            "sagging",
            "uniformness",
            "hydration",
            "redness",
        ]


class FaceScanSmoothingAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaceScanSmoothingAnalytics
        fields = [
            "created_at",
            "acne",
            "lines",
            "wrinkles",
            "pigmentation",
            "translucency",
            "quality",
            "eye_bags",
            "pores",
            "sagging",
            "uniformness",
            "hydration",
            "redness",
        ]


class StatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyStatistics
        fields = [
            "id",
            "skin_care",
            "well_being",
            "nutrition",
            "date",
        ]


class FaceScanCommentSerializer(serializers.ModelSerializer):
    comment = serializers.SerializerMethodField()

    class Meta:
        model = FaceScanComment
        fields = [
            "id",
            "face_scan",
            "comment",
            "created_at",
        ]

    def get_comment(self, obj):
        return obj.comment_message if obj.comment_message else obj.comment_template.name


class PredictionSerializer(serializers.ModelSerializer):
    prediction = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()

    class Meta:
        model = Prediction
        fields = [
            "id",
            "title",
            "image",
            "prediction",
            "date",
            "created_at",
        ]

    def get_prediction(self, obj) -> str:
        user_translations = self.context["user_translations"]
        template_id = obj.trans_template_id
        return user_translations[template_id]["prediction"] if template_id else obj.prediction_type

    def get_image(self, obj) -> Optional[str]:
        user_translations = self.context["user_translations"]
        template_id = obj.trans_template_id
        return user_translations[template_id]["image"] if template_id else None

    def get_title(self, obj) -> Optional[str]:
        user_translations = self.context["user_translations"]
        template_id = obj.trans_template_id
        return user_translations[template_id]["title"] if template_id else None


class UserTagSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    is_predefined = serializers.SerializerMethodField(method_name="check_predefined_tag")

    class Meta:
        model = UserTag
        fields = [
            "id",
            "name",
            "slug",
            "user",
            "is_predefined",
            "category",
        ]

    def validate(self, data):
        try:
            self.Meta.model(**data).clean()
        except CoreValidationError as err:
            raise serializers.ValidationError(err.message_dict)
        return data

    def check_predefined_tag(self, obj) -> bool:
        return not bool(obj.user_id)


class BaseHealthCareEventSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def validate(self, data):
        data_without_event_tags = copy.deepcopy(data)
        data_without_event_tags.pop("event_tags", None)
        try:
            self.Meta.model(**data_without_event_tags).clean()
        except CoreValidationError as err:
            raise serializers.ValidationError(err.messages)
        return data

    class Meta:
        model = HealthCareEvent
        fields = [
            "id",
            "user",
            "event_type",
            "name",
            "start_date",
            "event_tags",
            "created_at",
        ]
        extra_kwargs = {"event_tags": {"allow_empty": True, "write_only": True, "required": False}}


class MedicationEventSerializer(BaseHealthCareEventSerializer):
    event_type = serializers.HiddenField(default=HealthCareEventTypes.MEDICATION)
    medication_tags = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta(BaseHealthCareEventSerializer.Meta):
        fields = BaseHealthCareEventSerializer.Meta.fields + [
            "medication_type",
            "duration",
            "medication_tags",
        ]


class AppointmentEventSerializer(BaseHealthCareEventSerializer):
    event_type = serializers.HiddenField(default=HealthCareEventTypes.APPOINTMENT)
    appointment_tags = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta(BaseHealthCareEventSerializer.Meta):
        fields = BaseHealthCareEventSerializer.Meta.fields + [
            "time",
            "appointment_tags",
            "remind_me",
        ]


class MenstruationEventSerializer(BaseHealthCareEventSerializer):
    event_type = serializers.HiddenField(default=HealthCareEventTypes.MENSTRUATION)
    menstruation_tags = serializers.ListField(child=serializers.CharField(), read_only=True)
    name = serializers.HiddenField(default="")

    class Meta(BaseHealthCareEventSerializer.Meta):
        fields = BaseHealthCareEventSerializer.Meta.fields + [
            "duration",
            "menstruation_tags",
        ]


class StatisticsPurchaseSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def get_fields(self, *args, **kwargs):
        fields = super().get_fields(*args, **kwargs)
        request = self.context.get("request", None)
        if request and getattr(request, "action", None) == "complete":
            fields["receipt_data"].required = True
        return fields

    def save(self, **kwargs):
        try:
            statistics_purchase = super().save(**kwargs)
            PurchaseHistory.objects.create(purchase=statistics_purchase, status=statistics_purchase.status)
        except CoreValidationError as err:
            raise serializers.ValidationError(err.messages)

    class Meta:
        model = StatisticsPurchase
        fields = [
            "id",
            "user",
            "store_product",
            "store_name",
            "receipt_data",
            "purchase_started_on",
            "purchase_ends_after",
            "status",
        ]
        extra_kwargs = {
            "receipt_data": {"write_only": True, "required": False},
        }


class ImportScrappedProductsSerializer(serializers.Serializer):
    amazon_url = serializers.CharField()
    pages = serializers.IntegerField()


class DailyProductSetReviewSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    review_score = serializers.IntegerField(required=False)
    satisfaction_score = serializers.IntegerField(required=False)
    preference_score = serializers.IntegerField(required=False)
    efficiency_score = serializers.IntegerField(required=False)
    accessibility_score = serializers.IntegerField(required=False)
    easy_to_use_score = serializers.IntegerField(required=False)
    cost_score = serializers.IntegerField(required=False)

    def update(self, validated_data):  # noqa: C901
        product = DailyProduct.objects.get(id=validated_data.get("product_id"))
        product.review_score = validated_data.get("review_score")
        if validated_data.get("satisfaction_score"):
            product.satisfaction_score = validated_data.get("satisfaction_score")
        if validated_data.get("preference_score"):
            product.preference_score = validated_data.get("preference_score")
        if validated_data.get("efficiency_score"):
            product.efficiency_score = validated_data.get("efficiency_score")
        if validated_data.get("accessibility_score"):
            product.accessibility_score = validated_data.get("accessibility_score")
        if validated_data.get("easy_to_use_score"):
            product.easy_to_use_score = validated_data.get("easy_to_use_score")
        elif not validated_data.get("easy_to_use_score") and validated_data.get("accessibility_score"):
            product.easy_to_use_score = validated_data.get("accessibility_score")
        if validated_data.get("cost_score"):
            product.cost_score = validated_data.get("cost_score")
        product.save()

    def validate_review_score(self, review_score):
        if review_score > 5 or review_score < 0:
            raise ValidationError("review score must be between 0 and 5")
        return review_score

    def validate_satisfaction_score(self, satisfaction_score):
        if satisfaction_score > 5 or satisfaction_score < 0:
            raise ValidationError("satisfaction score must be between 0 and 5")
        return satisfaction_score

    def validate_preference_score(self, preference_score):
        if preference_score > 5 or preference_score < 0:
            raise ValidationError("preference score must be between 0 and 5")
        return preference_score

    def validate_efficiency_score(self, efficiency_score):
        if efficiency_score > 5 or efficiency_score < 0:
            raise ValidationError("efficiency score must be between 0 and 5")
        return efficiency_score

    def validate_accessibility_score(self, accessibility_score):
        if accessibility_score > 5 or accessibility_score < 0:
            raise ValidationError("accessibility score must be between 0 and 5")
        return accessibility_score

    def validate_easy_to_use_score(self, easy_to_use_score):
        if easy_to_use_score > 5 or easy_to_use_score < 0:
            raise ValidationError("easy_to_use score must be between 0 and 5")
        return easy_to_use_score

    def validate_cost_score(self, cost_score):
        if cost_score > 5 or cost_score < 0:
            raise ValidationError("cost score must be between 0 and 5")
        return cost_score

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if not instance.easy_to_use_score and instance.accessibility_score:
            representation["easy_to_use_score"] = instance.accessibility_score
        else:
            representation["easy_to_use_score"] = 0
        return representation
