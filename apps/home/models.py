import logging
import uuid

from ckeditor.fields import RichTextField
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import QuerySet
from solo.models import SingletonModel

from apps.content import AboutAndNoticeSectionType
from apps.routines import PredictionTypes
from apps.utils.models import BaseModel, BaseTranslationModel
from apps.utils.validation import check_template, validate_image_file_extensions

LOGGER = logging.getLogger("app")


class SiteConfiguration(SingletonModel):
    enabled_languages = models.ManyToManyField("translations.Language", related_name="enabled_inform_languages")
    default_language = models.ForeignKey(
        "translations.Language",
        related_name="default_inform_language",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    app_version_minimal_supported = models.CharField(max_length=50, blank=True, default="")
    app_version_latest = models.CharField(max_length=50, blank=True, default="")
    manifest_version = models.CharField(max_length=300, default="1")
    password_renewal_template = models.ForeignKey(
        "home.EmailTemplate",
        related_name="password_renewal_template",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    verify_email_template = models.ForeignKey(
        "home.EmailTemplate",
        related_name="verify_email_template",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    invalid_face_scan_notification_template = models.ForeignKey(
        "home.NotificationTemplate",
        related_name="invalid_face_scan_notification_template",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    face_analysis_completed_notification_template = models.ForeignKey(
        "home.NotificationTemplate",
        related_name="face_analysis_completed_notification_template",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    appointment_reminder_notification_template = models.ForeignKey(
        "home.NotificationTemplate",
        related_name="appointment_reminder_notification_template",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    face_scan_reminder_notification_template = models.ForeignKey(
        "home.NotificationTemplate",
        related_name="face_scan_reminder_notification_template",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    daily_questionnaire_reminder_notification_template = models.ForeignKey(
        "home.NotificationTemplate",
        related_name="daily_questionnaire_reminder_notification_template",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    monthly_statistics_notification_template = models.ForeignKey(
        "home.NotificationTemplate",
        related_name="monthly_statistics_notification_template",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    dashboard_order = models.ForeignKey(
        "home.DashboardOrder",
        related_name="dashboard_order",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    skin_journey = models.ForeignKey(
        "home.DashboardElement",
        related_name="skin_journey",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    shop_block = models.ForeignKey(
        "home.DashboardElement",
        related_name="shop_block",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    scan_duration = models.PositiveSmallIntegerField(help_text="Face scan duration in days", default=3)
    android_payments_enabled = models.BooleanField(default=True)
    ios_payments_enabled = models.BooleanField(default=False, verbose_name="IOS payments enabled")

    class Meta:
        verbose_name = "Site Configuration"

    @staticmethod
    def get_localized_email_template(email, language=None):
        if not language:
            # Lets use system default language if no other is present
            language = settings.DEFAULT_LANGUAGE

        template = email.email_template_translations.filter(language__code=language.lower()).first()
        if not template:
            LOGGER.error("No template %s with language %s", email, language)
        return template

    def get_password_renewal_template(self, language):
        if self.password_renewal_template:
            template = self.get_localized_email_template(self.password_renewal_template, language)
            return template
        return None

    def get_verification_template(self, language):
        if self.verify_email_template:
            template = self.get_localized_email_template(self.verify_email_template, language)
            return template
        return None

    def save(self, *args, **kwargs):
        self.manifest_version = uuid.uuid4().hex
        return super(SiteConfiguration, self).save(*args, **kwargs)


class EmailTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class EmailTemplateTranslation(models.Model):
    content = RichTextField()
    language = models.ForeignKey(
        "translations.Language",
        default=settings.DEFAULT_LANGUAGE,
        on_delete=models.SET_DEFAULT,
    )
    subject = models.CharField(max_length=100)
    template = models.ForeignKey(
        "home.EmailTemplate",
        related_name="email_template_translations",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = (("template", "language"),)

    def __str__(self):
        return f"{self.subject} {self.language}"

    def clean(self):
        check_template(self.content)


class AboutAndNoticeSection(BaseModel):
    name = models.CharField(help_text="Technical name.", max_length=255)
    type = models.CharField(  # noqa: A003, VNE003
        max_length=16, choices=AboutAndNoticeSectionType.get_choices(), blank=True
    )
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["type", "version"], name="One version per type"),
            models.UniqueConstraint(fields=["name", "version"], name="Unique name per version"),
        ]

    def clean(self):
        latest_version = self.get_latest_version(self.type)
        if latest_version and self.version != latest_version.version + 1:
            raise ValidationError(f"Version should be {latest_version.version + 1}")

    @classmethod
    def get_latest_version(cls, type_value: str) -> "AboutAndNoticeSection":
        return cls.get_latest_versions().filter(type=type_value).first()

    @classmethod
    def get_latest_versions(cls) -> QuerySet:
        return cls.objects.order_by("type", "-version").distinct("type")

    def __str__(self):
        return f"{self.type} v{self.version} {self.name}"


class UserAcceptedAboutAndNoticeSection(BaseModel):
    user = models.ForeignKey(
        "users.User",
        related_name="user_accepted_about_and_notice_section",
        on_delete=models.PROTECT,
    )
    about_and_notice_section = models.ForeignKey(
        "AboutAndNoticeSection",
        related_name="user_accepted_about_and_notice_section",
        on_delete=models.CASCADE,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "about_and_notice_section"],
                name="One about_and_notice_section per user",
            )
        ]


class AboutAndNoticeSectionTranslation(BaseTranslationModel):
    section = models.ForeignKey("AboutAndNoticeSection", related_name="translations", on_delete=models.CASCADE)
    content = RichTextField()

    class Meta(BaseTranslationModel.Meta):
        constraints = [models.UniqueConstraint(fields=["language", "section"], name="One language per section")]


class DashboardOrder(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    core_program = models.PositiveIntegerField(validators=[MaxValueValidator(5), MinValueValidator(1)])
    recipes = models.PositiveIntegerField(validators=[MaxValueValidator(5), MinValueValidator(1)])
    skin_tools = models.PositiveIntegerField(validators=[MaxValueValidator(5), MinValueValidator(1)])
    skin_school = models.PositiveIntegerField(validators=[MaxValueValidator(5), MinValueValidator(1)])
    skin_stories = models.PositiveIntegerField(validators=[MaxValueValidator(5), MinValueValidator(1)])

    class Meta:
        verbose_name_plural = "Dashboard Order"

    def clean(self):
        order_fields = [
            self.core_program,
            self.recipes,
            self.skin_tools,
            self.skin_school,
            self.skin_stories,
        ]
        if len(order_fields) > len(set(order_fields)):
            raise ValidationError("Order fields must not have the same values")

    def __str__(self):
        return self.name


class DashboardElement(BaseModel):
    name = models.CharField(help_text="Technical name.", unique=True, max_length=255)
    image = models.ImageField(upload_to="dashboard_images")

    def __str__(self):
        return self.name


class DashboardElementTranslation(BaseTranslationModel):
    dashboard_element = models.ForeignKey("DashboardElement", related_name="translations", on_delete=models.CASCADE)
    content = models.TextField()

    class Meta(BaseTranslationModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["language", "dashboard_element"],
                name="One language per dashboard element",
            )
        ]


class NotificationTemplate(BaseModel):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class NotificationTemplateTranslation(BaseModel):
    title = models.CharField(max_length=255)
    body = models.TextField()
    language = models.ForeignKey(
        "translations.Language",
        default=settings.DEFAULT_LANGUAGE,
        on_delete=models.SET_DEFAULT,
    )
    template = models.ForeignKey(
        "home.NotificationTemplate",
        related_name="translations",
        on_delete=models.CASCADE,
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["template", "language"], name="One template per language")]

    def __str__(self):
        return f"{self.title} {self.language}"


class FaceScanCommentTemplate(BaseModel):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class FaceScanCommentTemplateTranslation(BaseModel):
    title = models.CharField(max_length=255)
    body = models.TextField()
    language = models.ForeignKey(
        "translations.Language",
        default=settings.DEFAULT_LANGUAGE,
        on_delete=models.SET_DEFAULT,
    )
    template = models.ForeignKey(
        "home.FaceScanCommentTemplate",
        related_name="face_scan_comment_translations",
        on_delete=models.CASCADE,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["template", "language"],
                name="One comment template per language",
            )
        ]

    def __str__(self):
        return f"{self.title} {self.language}"


class PredictionTemplate(BaseModel):
    name = models.CharField(max_length=100, choices=PredictionTypes.get_choices(), unique=True)

    def __str__(self):
        return self.name


class PredictionTemplateTranslation(BaseModel):
    title = models.CharField(max_length=255)
    image = models.FileField(
        upload_to="prediction_images",
        validators=[validate_image_file_extensions],
        blank=True,
        default="",
    )
    body = models.TextField()
    language = models.ForeignKey(
        "translations.Language",
        default=settings.DEFAULT_LANGUAGE,
        on_delete=models.SET_DEFAULT,
    )
    template = models.ForeignKey(
        "home.PredictionTemplate",
        related_name="prediction_translations",
        on_delete=models.CASCADE,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["template", "language"],
                name="One prediction template per language",
            )
        ]

    def __str__(self):
        return f"{self.title} {self.language}"


class Review(models.Model):
    username = models.CharField(max_length=255)
    description = models.TextField()
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    def __str__(self):
        return f"{self.username} - {self.rating}/5"


class GlobalVariables(models.Model):
    indian_paywall = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.id} global settings"
