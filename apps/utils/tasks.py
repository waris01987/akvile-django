import logging
from typing import List, Optional

from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification

from apps.celery import app
from apps.home.models import (
    EmailTemplateTranslation,
    SiteConfiguration,
    NotificationTemplateTranslation,
)
from apps.routines import (
    FaceScanNotificationTypes,
    PUSH_NOTIFICATION_TYPE_TO_CLICK_ACTION_LINK,
)
from apps.translations.exceptions import (
    MissingTemplateException,
    MissingTemplateTranslationException,
)
from apps.utils.email import render_email_template_with_base, send_email
from apps.utils.helpers import send_push_notifications
from apps.utils.scrape import AmazonScrapper

LOGGER = logging.getLogger("app")


@app.task
def send_email_task(  # noqa: CFQ002
    email: str,
    template: str,
    category: Optional[str] = None,
    context: Optional[dict] = None,
    language: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
):
    """
    Email send task, which firstly collects all the information from SiteConfiguration
    and then calls send_email function.
    Example call:
    send_email_task.delay('some@email.com', VERIFICATION_EMAIL_TEMPLATE, 'Verify Email', {'context': 'value'}, 'en')
    """
    try:
        LOGGER.info("sending email %s to %s ", template, email)
        translation = _get_translation(template, language)
        html_message = render_email_template_with_base(
            html_content=translation.content,
            context=context,
            subject=translation.subject,
        )
        send_email(
            email=email,
            subject=translation.subject,
            html_message=html_message,
            category=category,
            cc=cc,
            bcc=bcc,
        )
    except Exception as e:  # noqa: B902
        LOGGER.error("Error during sending %s: %s ", translation, e)  # noqa: G200


def _get_translation(template: str, language: str) -> Optional[EmailTemplateTranslation]:
    """
    Gets translation for template.
    Accepts template to be a method or a field of site config.
    This "flexibility" is temporary, while refactoring is in progress:
    - Method is accepted for old parts.
    = Field is accepted for new parts (idea: to avoid the need to create
        duplicated "get_" methods in site config)
    """

    site_config = SiteConfiguration.get_solo()
    site_config_member = getattr(site_config, template)

    if callable(site_config_member):
        return site_config_member(language)

    template = site_config_member
    if template:
        if translation := site_config.get_localized_email_template(template, language):
            return translation
        else:
            error_msg = f"No notification translation {translation}"
            LOGGER.error(error_msg)
            raise MissingTemplateTranslationException(error_msg)
    else:
        error_msg = f"No notification template {template}"
        LOGGER.error(error_msg)
        raise MissingTemplateException(error_msg)


@app.task
def generate_and_send_notification(
    notification_template_pk: int,
    notification_type: FaceScanNotificationTypes,
    language_pk: str,
    device_pks: List[int],
) -> None:
    LOGGER.info("Sending push notifications [%s].", notification_type)
    notification_translation = NotificationTemplateTranslation.objects.filter(
        template_id=notification_template_pk, language_id=language_pk
    ).first()
    devices = FCMDevice.objects.filter(pk__in=device_pks)
    if notification_translation and devices.exists():
        send_push_notifications(
            devices,
            message=_generate_message_from_translation(notification_translation, notification_type),
        )
    else:
        LOGGER.error(
            "Could not send push notifications [%s] due to not having translation or devices.",
            notification_type,
        )


def _generate_message_from_translation(
    notification_translation: NotificationTemplateTranslation,
    notification_type: FaceScanNotificationTypes,
) -> Message:
    return Message(
        data={
            "link": PUSH_NOTIFICATION_TYPE_TO_CLICK_ACTION_LINK[notification_type],
            "type": "face_scan",
        },
        notification=Notification(title=notification_translation.title, body=notification_translation.body),
    )


@app.task
def import_products_from_amazon(amazon_url, pages) -> None:
    LOGGER.info(f"Starting importing {pages} pages of products from amazon link: {amazon_url}")
    AmazonScrapper.run_products_page(amazon_url=amazon_url, pages=pages)
