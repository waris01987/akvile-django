import logging

from django.contrib.auth import authenticate, password_validation, user_logged_in
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateformat import format as datetime_format
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.serializers import (
    PasswordField,
    TokenObtainPairSerializer,
)
from rest_social_auth.serializers import (
    JWTPairSerializer,
    UserJWTPairSerializer,
    OAuth2InputSerializer,
)

from apps.content import AboutAndNoticeSectionType
from apps.home.models import AboutAndNoticeSection
from apps.routines import PurchaseStatus
from apps.routines.models import StatisticsPurchase
from apps.translations.models import Language
from apps.users import SocialClient
from apps.users.models import PasswordKey, User, UserSettings
from apps.utils.error_codes import Errors
from apps.utils.token import get_token

LOGGER = logging.getLogger("app")


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        return get_token(user)


def use_password_validators(password: str, user: User) -> None:  # noqa
    password_validators = password_validation.get_default_password_validators()
    for validator in password_validators:
        try:
            validator.validate(password, user)  # type: ignore
        except ValidationError:
            if isinstance(validator, password_validation.UserAttributeSimilarityValidator):
                raise ValidationError(Errors.USER_ATRIBUTE_SIMILARITY_VALIDATION.value)
            if isinstance(validator, password_validation.MinimumLengthValidator):
                raise ValidationError(Errors.MINIMUM_LENGTH_VALIDATION.value)
            if isinstance(validator, password_validation.CommonPasswordValidator):
                raise ValidationError(Errors.COMMON_PASSWORD_VALIDATION.value)
            if isinstance(validator, password_validation.NumericPasswordValidator):
                raise ValidationError(Errors.NUMERIC_PASSWOD_VALIDATION.value)


class BaseEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(
        max_length=255,
        required=True,
        error_messages={
            "invalid": Errors.INVALID_EMAIL.value,
            "required": Errors.EMAIL_REQUIRED.value,
        },
    )


class SignUpSerializer(BaseEmailSerializer):
    first_name = serializers.CharField(max_length=255, required=True)
    password = serializers.CharField(write_only=True)
    terms_of_service = serializers.IntegerField(write_only=True)
    privacy_policy = serializers.IntegerField(write_only=True)

    def validate(self, attrs):
        attrs["email"] = attrs["email"].lower()
        if User.objects.filter(email=attrs["email"]).exists():
            raise exceptions.ValidationError(Errors.EMAIL_ALREADY_EXISTS.value)
        return attrs

    def validate_password(self, attr):
        user = self.context["request"].user
        use_password_validators(attr, user)
        return attr

    def validate_terms_of_service(self, attr):
        latest_terms_of_service = AboutAndNoticeSection.get_latest_version(
            AboutAndNoticeSectionType.TERMS_OF_SERVICE.value
        )
        if attr != latest_terms_of_service.id:
            raise exceptions.ValidationError(Errors.INCORRECT_TERMS_OF_SERVICE_VERSION.value)
        return latest_terms_of_service

    def validate_privacy_policy(self, attr):
        latest_privacy_policy = AboutAndNoticeSection.get_latest_version(AboutAndNoticeSectionType.PRIVACY_POLICY.value)
        if attr != latest_privacy_policy.id:
            raise exceptions.ValidationError(Errors.INCORRECT_PRIVACY_POLICY_VERSION.value)
        return latest_privacy_policy

    @transaction.atomic
    def create(self, validated_data):
        terms_of_service = validated_data.pop("terms_of_service")
        privacy_policy = validated_data.pop("privacy_policy")
        user = User.objects.create_user(**validated_data)
        user.create_activation_key()
        user.user_accepted_about_and_notice_section.create(about_and_notice_section=terms_of_service)
        user.user_accepted_about_and_notice_section.create(about_and_notice_section=privacy_policy)
        return user


class LoginSerializer(CustomTokenObtainPairSerializer):
    default_error_messages = {
        "no_active_account": Errors.BAD_CREDENTIALS.value,
    }

    token = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Not defined as class variables since DRF ignores class variables if its already defined in self.fields
        # And simple-JWT defines username_field via self.fields
        self.fields[self.username_field] = serializers.EmailField(
            write_only=True,
            required=True,
            error_messages={
                "invalid": Errors.INVALID_EMAIL.value,
                "required": Errors.FIELD_IS_REQUIRED.value,
            },
        )
        self.fields["password"] = PasswordField(error_messages={"required": Errors.FIELD_IS_REQUIRED.value})

    def validate(self, attrs):
        try:
            validated_data = super(LoginSerializer, self).validate(attrs)
        except exceptions.AuthenticationFailed:
            raise serializers.ValidationError(Errors.BAD_CREDENTIALS.value, code="authorization")

        if not self.user.is_verified:
            raise serializers.ValidationError(Errors.USER_EMAIL_NOT_VERIFIED.value, code="authorization")

        validated_data["token"] = validated_data.pop("access")
        return validated_data

    def create(self, validated_data):
        user_logged_in.send(sender=self.__class__, request=self.context["request"], user=self.user)
        return validated_data


class UserSerializer(serializers.ModelSerializer):
    gender = serializers.SerializerMethodField()
    questionnaire_id = serializers.SerializerMethodField()
    is_questionnaire_finished = serializers.ReadOnlyField()
    is_questionnaire_started = serializers.ReadOnlyField()
    active_subscriptions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "email",
            "avatar",
            "gender",
            "geolocation",
            "device",
            "operating_system",
            "questionnaire_id",
            "is_questionnaire_finished",
            "is_questionnaire_started",
            "date_joined",
            "active_subscriptions",
            "has_accepted_latest_terms_of_service",
            "has_accepted_latest_privacy_policy",
            "health_data",
        )
        extra_kwargs = {
            "email": {"read_only": True},
            "date_joined": {"read_only": True},
        }

    def get_gender(self, instance):
        if instance.is_questionnaire_finished:
            return instance.questionnaire.gender
        return None

    def get_questionnaire_id(self, instance):
        if instance.is_questionnaire_finished:
            return instance.questionnaire.id
        return None

    def get_active_subscriptions(self, instance):
        current_time = timezone.now()
        active_subscriptions = StatisticsPurchase.objects.filter(
            user=instance,
            status__in=[PurchaseStatus.COMPLETED.value, PurchaseStatus.EXPIRED.value],
            purchase_started_on__lt=current_time,
            purchase_ends_after__gt=current_time,
        )
        if active_subscriptions:
            active_subscription_list = []
            for subscription in active_subscriptions:
                active_subscription_list.append(
                    {
                        "id": subscription.id,
                        "started_on": subscription.purchase_started_on,
                        "expires_on": subscription.purchase_ends_after,
                        "store_name": subscription.store_name,
                        "store_product": subscription.store_product_id,
                    }
                )
            return active_subscription_list
        return None


class ChangeLanguageSerializer(serializers.Serializer):
    language = serializers.CharField(max_length=10, required=True)

    class Meta:
        fields = ("language",)

    @staticmethod
    def validate_language(attrs):
        if not Language.objects.filter(code=attrs).exists():
            raise serializers.ValidationError(Errors.NO_SUCH_LANGUAGE.value)
        return attrs


class BasePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=255, write_only=True, required=True)
    confirm_password = serializers.CharField(max_length=255, write_only=True, required=True)

    class Meta:
        fields = ("password", "confirm_password")

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("confirm_password"):
            raise serializers.ValidationError(Errors.PASSWORDS_NOT_EQUAL.value)
        return attrs


class ChangePasswordSerializer(BasePasswordSerializer):
    old_password = PasswordField(required=True, write_only=True)

    class Meta:
        fields = ("old_password", "password", "confirm_password")

    def validate_old_password(self, attr):
        if not authenticate(email=self.context["request"].user.email, password=attr):
            raise serializers.ValidationError(Errors.PASSWORD_IS_INCORRECT.value)
        return attr

    def to_representation(self, instance):
        refresh = get_token(self.context["request"].user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}

    def create(self, validated_data):
        self.context["request"].user.set_password(validated_data["password"])
        self.context["request"].user.save()
        return {}


class ForgottenPasswordSerializer(BaseEmailSerializer):
    def create(self, validated_data):
        user = User.objects.filter(email__iexact=validated_data["email"]).first()

        if not user:
            # To prevent registered email checking we just do nothing here
            return {}

        PasswordKey.objects.filter(user=user).delete()
        user.create_new_password_token()
        return {}


class VerificationEmailResendSerializer(BaseEmailSerializer):
    def create(self, validated_data):
        user = User.objects.filter(email__iexact=validated_data["email"], is_verified=False).first()

        if not user:
            # To prevent registered email checking we just do nothing here
            return {}

        user.create_activation_key()
        return {}


class JWTWithClaimPairSerializer(JWTPairSerializer):
    def get_token_payload(self, user):
        payload = super().get_token_payload(user)
        payload["datetime_claim"] = int(datetime_format(user.password_last_change, "U"))
        return payload


class UserJWTWithClaimPairSerializer(UserJWTPairSerializer):
    is_new = serializers.SerializerMethodField()

    def get_is_new(self, user):
        return getattr(user, "is_new", None)

    def get_token_payload(self, user):
        payload = super().get_token_payload(user)
        payload["datetime_claim"] = int(datetime_format(user.password_last_change, "U"))
        LOGGER.info(f"social token payload: {payload}")
        payload.pop("chat_gpt_history", None)
        payload.pop("geo_updated", None)
        return payload


class MultiClientOAuth2InputSerializer(OAuth2InputSerializer):
    client_type = serializers.ChoiceField(choices=SocialClient.get_choices(), required=False)


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = [
            "is_face_scan_reminder_active",
            "is_daily_questionnaire_reminder_active",
        ]
