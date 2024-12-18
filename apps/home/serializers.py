from typing import OrderedDict, Union

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from apps.content import AboutAndNoticeSectionType
from apps.home.models import (
    AboutAndNoticeSection,
    UserAcceptedAboutAndNoticeSection,
    Review,
    GlobalVariables,
)
from apps.utils.error_codes import Errors


class AboutSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    def get_title(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].title
        return obj.name

    def get_content(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].content
        return ""

    class Meta:
        model = AboutAndNoticeSection
        fields = [
            "id",
            "title",
            "content",
            "type",
            "version",
            "created_at",
            "updated_at",
        ]


class UserAboutSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAcceptedAboutAndNoticeSection
        fields = ["id", "user", "about_and_notice_section", "created_at", "updated_at"]
        validators = [
            UniqueTogetherValidator(
                queryset=UserAcceptedAboutAndNoticeSection.objects.all(),
                fields=["user", "about_and_notice_section"],
            )
        ]

    def validate(self, attrs: dict) -> dict:
        error_messages = {
            AboutAndNoticeSectionType.TERMS_OF_SERVICE.value: Errors.INCORRECT_TERMS_OF_SERVICE_VERSION.value,
            AboutAndNoticeSectionType.PRIVACY_POLICY.value: Errors.INCORRECT_PRIVACY_POLICY_VERSION.value,
        }
        latest_version = AboutAndNoticeSection.get_latest_version(attrs["about_and_notice_section"].type)
        if attrs["about_and_notice_section"] != latest_version:
            raise serializers.ValidationError(error_messages[attrs["about_and_notice_section"].type])
        return attrs

    def to_internal_value(self, data: Union[int, dict]) -> OrderedDict:
        if (request := self.context.get("request")) and isinstance(data, int):
            data = {"about_and_notice_section": data, "user": request.user.id}
        return super().to_internal_value(data)


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "username", "description", "rating"]


class GlobalVariablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalVariables
        fields = ["indian_paywall"]
