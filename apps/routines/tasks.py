import datetime
import logging

from django.db.models import Q, ExpressionWrapper, F, DurationField
from django.utils import timezone
from firebase_admin.messaging import Message, Notification

from apps.celery import app
from apps.home.models import SiteConfiguration, NotificationTemplateTranslation
from apps.routines import HealthCareEventTypes, PurchaseStatus
from apps.routines.models import (
    DailyProduct,
    HealthCareEvent,
    FaceScanAnalytics,
    FaceScanSmoothingAnalytics,
    FaceScan,
    DailyQuestionnaire,
    StatisticsPurchase,
)
from apps.users.models import User
from apps.utils.helpers import send_push_notifications

LOGGER = logging.getLogger("app")


@app.task
def send_reminder_notification_for_appointments(  # noqa: C901
    appointment_event_pks: list[int] = None,
) -> None:
    """Sends reminder push notifications for appointment events"""
    current_time = timezone.now()
    site_config = SiteConfiguration.get_solo()
    reminder_template = site_config.appointment_reminder_notification_template
    successful_reminder_pks = []
    if reminder_template:
        if appointment_event_pks:
            appointment_events = HealthCareEvent.objects.filter(
                event_type=HealthCareEventTypes.APPOINTMENT,
                remind_me=True,
                user__questionnaire__isnull=False,
                id__in=appointment_event_pks,
            )
        else:
            # filter appointments in next 24 hours
            filters = Q(
                time_diff__gte=datetime.timedelta(hours=24),
                time_diff__lt=datetime.timedelta(hours=25),
            )
            # or, filter appointments in next 1 hour if it is less than 24 hours
            filters |= Q(
                time_diff__gte=datetime.timedelta(hours=1),
                time_diff__lt=datetime.timedelta(hours=2),
            )

            appointment_events = (
                HealthCareEvent.objects.filter(
                    event_type=HealthCareEventTypes.APPOINTMENT,
                    remind_me=True,
                    is_reminder_sent=False,
                    user__questionnaire__isnull=False,
                )
                .annotate(
                    time_diff=ExpressionWrapper(
                        (F("start_date") + F("time")) - current_time,  # type:ignore
                        output_field=DurationField(),  # type:ignore
                    )
                )
                .filter(filters)
            )
        for event in appointment_events:
            if (translation := reminder_template.translations.filter(language_id=event.user.language.pk).first()) and (
                devices := event.user.fcmdevice_set.all()  # type: ignore
            ):
                try:
                    send_push_notifications(
                        devices,
                        message=generate_appointment_message(translation, event),
                    )
                    LOGGER.debug(
                        "Successfully sent reminder notification for event [%s].",
                        event.id,
                    )
                except Exception as err:  # noqa: B902
                    LOGGER.exception(
                        "Reminder notification sending failed for event [%s] due to [%s].",
                        event.id,
                        err,
                    )
                else:
                    successful_reminder_pks.append(event.id)
            else:
                LOGGER.error(
                    "Could not send reminder notifications for event [%s] due to not having translation or devices.",
                    event.id,
                )

        if successful_reminder_pks:
            appointment_events.filter(id__in=successful_reminder_pks).update(
                reminder_sent_at=current_time, is_reminder_sent=True
            )
    else:
        LOGGER.error("No template found for appointment reminder notification.")


def generate_appointment_message(
    notification_translation: NotificationTemplateTranslation,
    appointment_event: HealthCareEvent,
) -> Message:
    """Generates notification message from template translation and appoint event"""
    message_body = f"{notification_translation.body} {appointment_event.start_date} {appointment_event.time}."
    return Message(notification=Notification(title=notification_translation.title, body=message_body))


@app.task
def send_reminder_for_face_scans(eligible_user_pks: list[int] = None) -> None:
    """Sends reminder push notifications for users who are skipping face scan within max scan duration"""
    current_time = timezone.now()
    site_config = SiteConfiguration.get_solo()
    reminder_template = site_config.face_scan_reminder_notification_template

    if not reminder_template:
        LOGGER.error("No template found for face scan reminder notification.")
        return

    if eligible_user_pks:
        eligible_reminder_receiver_filter = Q(
            is_active=True,
            user_settings__is_face_scan_reminder_active=True,
            questionnaire__isnull=False,
            id__in=eligible_user_pks,
        )
    else:
        # fetching valid face scans which are within max scan duration (in days) from current time
        needed_period_start_time = current_time - datetime.timedelta(days=site_config.scan_duration)
        active_face_scan_users = FaceScanAnalytics.objects.filter(
            is_valid=True, created_at__gt=needed_period_start_time
        ).values_list("face_scan__user_id", flat=True)

        # getting eligible users for reminders who are active and has no valid face scan within max scan duration
        # (in days) from current time and reminder is active in user settings
        eligible_reminder_receiver_filter = (
            Q(
                is_active=True,
                user_settings__is_face_scan_reminder_active=True,
                questionnaire__isnull=False,
            )
            & ~Q(id__in=active_face_scan_users)
        )
    eligible_reminder_receivers = User.objects.filter(eligible_reminder_receiver_filter)
    for user in eligible_reminder_receivers:
        if (translation := reminder_template.translations.filter(language_id=user.language.pk).first()) and (
            devices := user.fcmdevice_set.all()  # type: ignore
        ):
            try:
                send_push_notifications(devices, message=generate_reminder_message(translation))
                LOGGER.debug(
                    "Successfully sent face scan reminder notification to user [%s].",
                    user.id,
                )
            except Exception as err:  # noqa: B902
                LOGGER.exception(
                    "Face scan reminder notification sending failed for user [%s] due to [%s].",
                    user.id,
                    err,
                )
        else:
            LOGGER.error(
                "Could not send face scan reminder notifications for user [%s] due to not having translation"
                " or devices.",
                user.id,
            )


@app.task
def send_reminder_for_daily_questionnaire(eligible_user_pks: list[int] = None) -> None:
    """Sends reminder push notifications for users who did not fill up daily questionnaire today"""
    current_time = timezone.now()
    site_config = SiteConfiguration.get_solo()
    reminder_template = site_config.daily_questionnaire_reminder_notification_template

    if not reminder_template:
        LOGGER.error("No template found for daily questionnaire reminder notification.")
        return

    if eligible_user_pks:
        eligible_reminder_receiver_filter = Q(
            is_active=True,
            user_settings__is_daily_questionnaire_reminder_active=True,
            id__in=eligible_user_pks,
            questionnaire__isnull=False,
        )
    else:
        # fetching  users who are active today and filled up daily questionnaire
        active_daily_questionnaire_users = DailyQuestionnaire.objects.filter(
            created_at__date=current_time.date()
        ).values_list("user_id", flat=True)

        # getting eligible users for reminders who are active and has no daily questionnaire answer today and has
        # enabled reminder in user settings
        eligible_reminder_receiver_filter = (
            Q(
                is_active=True,
                user_settings__is_daily_questionnaire_reminder_active=True,
                questionnaire__isnull=False,
            )
            & ~Q(id__in=active_daily_questionnaire_users)
        )

    eligible_reminder_receivers = User.objects.filter(eligible_reminder_receiver_filter)
    for user in eligible_reminder_receivers:
        if (translation := reminder_template.translations.filter(language_id=user.language.pk).first()) and (
            devices := user.fcmdevice_set.all()  # type: ignore
        ):
            try:
                send_push_notifications(devices, message=generate_reminder_message(translation))
                LOGGER.debug(
                    "Successfully sent daily questionnaire reminder notification to user [%s].",
                    user.id,
                )
            except Exception as err:  # noqa: B902
                LOGGER.exception(
                    "Daily questionnaire reminder notification sending failed for user [%s] due to [%s].",
                    user.id,
                    err,
                )
        else:
            LOGGER.error(
                "Could not send daily questionnaire reminder notifications for user [%s] due to not having translation"
                " or devices.",
                user.id,
            )


@app.task
def send_notification_about_monthly_statistics(  # noqa: C901
    eligible_user_pks: list[int] = None,
) -> None:
    """Sends push notifications to premium users about their monthly statistics being ready at the end of the month"""
    current_time = timezone.now()
    if not end_of_month(current_time):
        return

    site_config = SiteConfiguration.get_solo()
    notification_template = site_config.monthly_statistics_notification_template

    if not notification_template:
        LOGGER.error("No template found for monthly statistics notification.")
        return

    eligible_statistics_purchases = StatisticsPurchase.objects.filter(
        status=PurchaseStatus.COMPLETED.value,
        purchase_started_on__lt=current_time,
        purchase_ends_after__gt=current_time,
        user__questionnaire__isnull=False,
    )
    if eligible_user_pks:
        eligible_statistics_purchases = eligible_statistics_purchases.filter(user_id__in=eligible_user_pks)
    for purchase in eligible_statistics_purchases:
        translation = notification_template.translations.filter(language_id=purchase.user.language.pk).first()
        devices = purchase.user.fcmdevice_set.all()  # type: ignore
        if translation and devices:
            try:
                send_push_notifications(devices, message=generate_reminder_message(translation))
                LOGGER.debug(
                    "Successfully sent notification to user [%s] for statistics purchase [%s].",
                    purchase.user_id,
                    purchase.id,
                )
            except Exception as err:  # noqa: B902
                LOGGER.exception(
                    "Notification sending to user [%s] for statistics purchase [%s] failed due to [%s].",
                    purchase.user_id,
                    purchase.id,
                    err,
                )
        else:
            LOGGER.error(
                "Could not send reminder notifications to user [%s] for statistics purchase [%s] "
                "due to not having translation or devices.",
                purchase.user_id,
                purchase.id,
            )


@app.task
def connect_scrapped_product_to_daily_product(
    eligible_user_pks: list[int] = None,
) -> None:  # noqa: C901
    """Iterate through daily products to get names from parsed images using Google Lens"""
    daily_products_without_scrappped = DailyProduct.objects.filter(product_info=None).exclude(name="")[:20]
    if not daily_products_without_scrappped:
        return
    for daily_product in daily_products_without_scrappped:
        scrapped_product = daily_product.get_similar_scrapped_product_by_title(daily_product.name)
        if not scrapped_product:
            if daily_product.connect_scrapped_fail >= 5:
                daily_product.name = ""
                daily_product.connect_scrapped_fail = 0
                daily_product.image_parse_fail = 0
                daily_product.save()
                continue
            daily_product.connect_scrapped_fail += 1
            daily_product.save()
            continue
        daily_product.product_info = scrapped_product
        daily_product.save()


def generate_reminder_message(
    notification_translation: NotificationTemplateTranslation,
) -> Message:
    """Generates notification message from template translation"""
    return Message(notification=Notification(title=notification_translation.title, body=notification_translation.body))


def end_of_month(dt: datetime.datetime) -> bool:
    todays_month = dt.month
    tomorrows_month = (dt + datetime.timedelta(days=1)).month
    return bool(tomorrows_month != todays_month)


@app.task
def update_sagging_parameter_for_face_scan_analytics(
    eligible_user_pks: list[int] = None,
) -> None:  # noqa: C901
    """Iterate through FaceScanSmoothingAnalytics and FaceScanAnalytics to update sagging parameter"""
    face_scans = FaceScan.objects.filter(updated_sagging=False)[:500]
    total_facescans = len(face_scans)
    no_data_facescans = 0
    updated_facescans = 0
    for face_scan in face_scans:
        try:
            analytics = face_scan.analytics
            smooth_analytics = face_scan.smoothing_analytics
        except (
            FaceScanAnalytics.DoesNotExist,
            FaceScanSmoothingAnalytics.DoesNotExist,
        ):
            face_scan.updated_sagging = True
            face_scan.save()
            no_data_facescans += 1
            continue
        if not analytics.is_valid:
            face_scan.updated_sagging = True
            face_scan.save()
            no_data_facescans += 1
            continue
        for raw_data in smooth_analytics.raw_data:
            if raw_data["algorithm_tech_name"] == "selfie_v2.sagging":
                analytics.sagging = raw_data["value"]
                smooth_analytics.sagging = raw_data["value"]
                face_scan.updated_sagging = True
                face_scan.save()
                smooth_analytics.save()
                analytics.save()
                updated_facescans += 1
    LOGGER.info(
        f"total_facescans: {total_facescans}\n"
        f"no_data_facescans: {no_data_facescans}\n"
        f"updated_facescans: {updated_facescans}"
    )


@app.task
def update_brand_from_new_brand(  # noqa: C901
    eligible_user_pks: list[int] = None,
) -> None:
    from apps.csv_read.read import UpdateDailyProductBrand

    UpdateDailyProductBrand.run()


@app.task
def update_category(  # noqa: C901
    eligible_user_pks: list[int] = None,
) -> None:
    from apps.csv_read.read import UpdateChatgptMessageCategory

    UpdateChatgptMessageCategory.run()
