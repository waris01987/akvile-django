from typing import Optional

from django.contrib import admin
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.utils.html import escape, format_html
import nested_admin
from rest_framework.request import Request
from solo.admin import SingletonModelAdmin
from tabbed_admin import TabbedModelAdmin

from apps.home.models import (
    DashboardElement,
    DashboardElementTranslation,
    DashboardOrder,
    SiteConfiguration,
    EmailTemplateTranslation,
    EmailTemplate,
    AboutAndNoticeSection,
    AboutAndNoticeSectionTranslation,
    NotificationTemplate,
    NotificationTemplateTranslation,
    FaceScanCommentTemplate,
    FaceScanCommentTemplateTranslation,
    PredictionTemplate,
    PredictionTemplateTranslation,
    UserAcceptedAboutAndNoticeSection,
    Review,
    GlobalVariables,
)


@admin.register(SiteConfiguration)
class ConfigAdmin(TabbedModelAdmin, SingletonModelAdmin):
    readonly_fields = ("manifest_version", "regenerate_cache")

    tab_overview = (
        (
            None,
            {
                "fields": (
                    (
                        "default_language",
                        "enabled_languages",
                    ),
                    (
                        "regenerate_cache",
                        "manifest_version",
                        "scan_duration",
                    ),
                )
            },
        ),
    )

    tab_emails = (
        (
            None,
            {
                "fields": (
                    (
                        "password_renewal_template",
                        "verify_email_template",
                    ),
                )
            },
        ),
    )

    tab_version_control = (
        (
            None,
            {
                "fields": (
                    (
                        "app_version_minimal_supported",
                        "app_version_latest",
                    ),
                )
            },
        ),
    )

    tab_dashboard = (
        (
            None,
            {
                "fields": (
                    (
                        "dashboard_order",
                        "skin_journey",
                        "shop_block",
                    ),
                )
            },
        ),
    )

    tab_templates = (
        (
            None,
            {
                "fields": (
                    (
                        "invalid_face_scan_notification_template",
                        "face_analysis_completed_notification_template",
                        "appointment_reminder_notification_template",
                        "face_scan_reminder_notification_template",
                        "daily_questionnaire_reminder_notification_template",
                        "monthly_statistics_notification_template",
                    ),
                )
            },
        ),
    )

    tab_payments = (
        (
            None,
            {
                "fields": (
                    ("android_payments_enabled",),
                    ("ios_payments_enabled",),
                )
            },
        ),
    )

    tabs = [
        ("Overview", tab_overview),
        ("Emails", tab_emails),
        ("Version Control", tab_version_control),
        ("Dashboard", tab_dashboard),
        ("Templates", tab_templates),
        ("Payments", tab_payments),
    ]

    @staticmethod
    def regenerate_cache(*args):
        hyper = format_html('<a class="button" href="/admin/regenerate_cache/">Regenerate cache</a>', *args)
        hyper.short_description = "Regenerate cache"
        hyper.allow_tags = True
        return hyper


class TemplateTranslationInline(admin.TabularInline):
    model = EmailTemplateTranslation
    extra = 0


@admin.register(EmailTemplate)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("name",)

    inlines = [TemplateTranslationInline]


@admin.register(GlobalVariables)
class GlobalVariablesAdmin(admin.ModelAdmin):
    list_display = ("indian_paywall",)


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = "action_time"

    readonly_fields = [f.name for f in LogEntry._meta.fields]

    list_filter = ["content_type", "action_flag"]

    search_fields = ["object_repr", "change_message"]

    list_display = [
        "action_time",
        "user",
        "content_type",
        "object_link",
        "action_flag",
        "get_change_message",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @staticmethod
    def object_link(obj):
        if obj.action_flag == DELETION:
            link = escape(obj.object_repr)
        else:
            link = '<a href="%s">%s</a>' % (
                obj.get_admin_url(),
                escape(obj.object_repr),
            )
        link = format_html(link)
        link.allow_tags = True
        link.admin_order_field = "object_repr"
        link.short_description = "object"
        return link

    @staticmethod
    def action_flag(obj):
        action_map = {
            DELETION: "Deletion",
            CHANGE: "Change",
            ADDITION: "Addition",
        }
        return action_map.get(obj.action_flag, obj.action_flag)


class AboutAndNoticeSectionTranslationInline(nested_admin.NestedTabularInline):
    model = AboutAndNoticeSectionTranslation
    extra = 0


@admin.register(AboutAndNoticeSection)
class AboutAndNoticeSectionAdmin(nested_admin.NestedModelAdmin):
    list_display = ["name", "type", "version"]
    search_fields = ["name", "translations__title"]
    inlines = [AboutAndNoticeSectionTranslationInline]


@admin.register(UserAcceptedAboutAndNoticeSection)
class UserAcceptedAboutAndNoticeSectionAdmin(nested_admin.NestedModelAdmin):
    list_display = ["user", "about_and_notice_section"]

    def has_change_permission(self, request: Request, obj: Optional[UserAcceptedAboutAndNoticeSection] = None) -> bool:
        return False


@admin.register(DashboardOrder)
class DashboardOrderAdmin(admin.ModelAdmin):
    list_display = ["name"]


class DashboardElementTranslationInline(nested_admin.NestedTabularInline):
    model = DashboardElementTranslation
    extra = 0


@admin.register(DashboardElement)
class SkinJourneyAdmin(nested_admin.NestedModelAdmin):
    list_display = ["name"]
    search_fields = ["name", "translations__title"]
    inlines = [DashboardElementTranslationInline]


class NotificationTemplateTranslationInline(admin.TabularInline):
    model = NotificationTemplateTranslation
    extra = 0


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("name",)

    inlines = [NotificationTemplateTranslationInline]


class FaceScanCommentTemplateTranslationInline(admin.TabularInline):
    model = FaceScanCommentTemplateTranslation
    extra = 0


@admin.register(FaceScanCommentTemplate)
class FaceScanCommentTemplateAdmin(admin.ModelAdmin):
    list_display = ("name",)

    inlines = [FaceScanCommentTemplateTranslationInline]


class PredictionTemplateTranslationInline(admin.TabularInline):
    model = PredictionTemplateTranslation
    extra = 0


@admin.register(PredictionTemplate)
class PredictionTemplateAdmin(admin.ModelAdmin):
    list_display = ("name",)

    inlines = [PredictionTemplateTranslationInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "username", "description", "rating"]
    search_fields = ["username", "description"]
    list_filter = ["rating"]
