import logging
from typing import Dict, Any, Type, List, Union, Optional

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from fcm_django.models import FCMDevice
from import_export.formats import base_formats
from import_export.formats.base_formats import DEFAULT_FORMATS, TextFormat
from import_export_celery.admin import ExportJobForm, ExportJobAdmin
from import_export_celery.admin_actions import create_export_job_action
from import_export_celery.models import ImportJob, ExportJob
from rest_framework.request import Request

from apps.home.models import SiteConfiguration
from apps.routines import FaceScanNotificationTypes
from apps.routines.tasks import (
    send_reminder_for_daily_questionnaire,
    send_reminder_for_face_scans,
)
from apps.users.models import ActivationKey, User, PasswordKey
from apps.users.resources import UserResource
from apps.users.tasks import set_user_device_info
from apps.utils.mixins import CeleryExportMixin
from apps.utils.tasks import generate_and_send_notification

LOGGER = logging.getLogger("app")


class CustomUserAdmin(CeleryExportMixin, UserAdmin):
    resource_class = UserResource
    fieldsets = (
        (None, {"fields": ("password",)}),
        (
            _("Personal info"),
            {"fields": ("first_name", "last_name", "email", "password_last_change")},
        ),
        (_("Verification"), {"fields": ("is_verified",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
        (
            _("Extra info"),
            {
                "fields": (
                    "haut_ai_subject_id",
                    "health_data",
                    "chat_gpt_history",
                    "geo_updated",
                )
            },
        ),
        (
            _("Device info"),
            {
                "fields": (
                    "geolocation",
                    "device",
                    "operating_system",
                    "is_amplitude_synced",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

    list_display = [
        "id",
        "first_name",
        "last_name",
        "email",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "last_login",
        "health_data",
    ]
    ordering = ("-id",)
    search_fields = ("first_name", "last_name", "email")
    exclude = []
    actions = [
        create_export_job_action,
        "send_invalid_face_scan_notification",
        "send_success_face_scan_notification",
        "send_reminder_for_daily_questionnaire",
        "send_reminder_notification_for_daily_questionnaire",
        "send_reminder_notification_for_face_scan",
        "set_user_device_info_from_amplitude",
    ]

    @admin.action(description="Manually send face scan success push notification")  # type: ignore[attr-defined]
    def send_success_face_scan_notification(self, request, queryset) -> None:
        """Send success face scan push notification manually"""
        site_config = SiteConfiguration.get_solo()
        device_pks = FCMDevice.objects.filter(user__in=queryset).values_list("id", flat=True)
        language_pk = request.user.language.pk
        analysis_completed_notification_template = site_config.face_analysis_completed_notification_template
        if analysis_completed_notification_template:
            generate_and_send_notification(
                analysis_completed_notification_template.pk,
                FaceScanNotificationTypes.SUCCESS,
                language_pk,
                device_pks,
            )

    @admin.action(description="Manually send face scan invalid push notification")  # type: ignore[attr-defined]
    def send_invalid_face_scan_notification(self, request, queryset) -> None:
        """Send invalid face scan push notification manually"""
        site_config = SiteConfiguration.get_solo()
        device_pks = FCMDevice.objects.filter(user__in=queryset).values_list("id", flat=True)
        language_pk = request.user.language.pk
        invalid_face_notification_template = site_config.invalid_face_scan_notification_template
        if invalid_face_notification_template:
            generate_and_send_notification(
                invalid_face_notification_template.pk,
                FaceScanNotificationTypes.INVALID,
                language_pk,
                device_pks,
            )

    @admin.action(description="Manually send daily questionnaire reminder notification")  # type: ignore[attr-defined]
    def send_reminder_notification_for_daily_questionnaire(self, request, queryset) -> None:
        """Send daily questionnaire reminder push notification manually"""
        send_reminder_for_daily_questionnaire(queryset.values_list("id", flat=True))

    @admin.action(description="Manually send face scan reminder notification")  # type: ignore[attr-defined]
    def send_reminder_notification_for_face_scan(self, request, queryset) -> None:
        """Send face scan reminder push notification manually"""
        send_reminder_for_face_scans(queryset.values_list("id", flat=True))

    @admin.action(description="Set user device info from amplitude")  # type: ignore[attr-defined]
    def set_user_device_info_from_amplitude(self, request, queryset) -> None:
        """Set user device info from amplitude to users that don't already have it"""
        queryset_ids = (
            queryset.filter(Q(geolocation="") | Q(device="") | Q(operating_system=""))
            .exclude(is_amplitude_synced=True)
            .exclude(first_name=settings.DEACTIVATED_USER_SENSITIVE_DATA_FIELD)
            .order_by("-date_joined")
            .values_list("id", flat=True)
        )
        set_user_device_info.delay(list(queryset_ids))


admin.site.register(User, CustomUserAdmin)


@admin.register(ActivationKey)
class ActivationKeyAdmin(admin.ModelAdmin):
    list_display = ["user", "activation_key"]
    fields = [
        "user",
        "activation_key",
    ]

    def has_change_permission(self, request: Request, obj: Optional[ActivationKey] = None) -> bool:
        return False


@admin.register(PasswordKey)
class PasswordKeyAdmin(admin.ModelAdmin):
    fields = [
        "user",
        "password_key",
        "expires_at",
    ]
    readonly_fields = ["user", "password_key"]


admin.site.unregister(ImportJob)
admin.site.unregister(ExportJob)


class UpdateExportJobForm(ExportJobForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disabling sending email on completion to prevent unusual email sending
        # related problem after the exporting job which was turned on by default
        # from the library.
        self.fields["email_on_completion"].disabled = True
        self.fields["format"].widget = forms.Select(
            choices=[
                (f.CONTENT_TYPE, f().get_title())
                for f in DEFAULT_FORMATS
                if f().can_export() and f in self._get_allowed_formats()
            ]
        )

    def clean(self) -> Dict[str, Any]:
        data = super().clean()
        data["email_on_completion"] = False
        return data

    def _get_allowed_formats(self) -> List[Type[Union[TextFormat]]]:
        formats = [
            base_formats.CSV,
            base_formats.XLSX,
        ]
        return formats


@admin.register(ExportJob)
class CustomExportJobAdmin(ExportJobAdmin):
    """
    Customizing ExportAdmin by using UpdateExportJobForm to disable
    default email notification feature for celery export job
    """

    form = UpdateExportJobForm
