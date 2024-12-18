from unittest.mock import patch

from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification
from model_bakery.baker import make

from apps.home.models import NotificationTemplate, NotificationTemplateTranslation
from apps.routines import (
    FaceScanNotificationTypes,
    PUSH_NOTIFICATION_TYPE_TO_CLICK_ACTION_LINK,
)
from apps.utils.helpers import send_push_notifications
from apps.utils.tasks import (
    _generate_message_from_translation,
    generate_and_send_notification,
)
from apps.utils.tests_utils import BaseTestCase


class TestPushNotification(BaseTestCase):
    @patch("apps.utils.helpers.FCMDevice", autospec=True)
    def test_send_push_notification(self, FCMDevice):  # noqa: N803
        devices = make(FCMDevice, user=self.user, _quantity=2)
        message = Message(notification=Notification(title="test title", body="Sample notification message body"))
        send_push_notifications(devices, message)
        for device in devices:
            device.send_message.assert_called_with(message)

    def test_generate_message_for_push_notification(self):
        notification_template = make(NotificationTemplate)
        notification_translation = make(
            NotificationTemplateTranslation,
            template=notification_template,
            title="test title",
            body="test sample body",
        )
        message = _generate_message_from_translation(notification_translation, FaceScanNotificationTypes.SUCCESS)
        self.assertEqual(message.notification.title, notification_translation.title)
        self.assertEqual(message.notification.body, notification_translation.body)
        self.assertEqual(
            message.data["link"],
            PUSH_NOTIFICATION_TYPE_TO_CLICK_ACTION_LINK[FaceScanNotificationTypes.SUCCESS],
        )
        self.assertEqual(message.data["type"], "face_scan")

    @patch("apps.utils.tasks.send_push_notifications", autospec=True)
    def test_generate_and_send_notification(self, mocked_sender):
        devices = make(FCMDevice, user=self.user, _quantity=2, _fill_optional=True)
        device_pks = [device.id for device in devices]
        notification_template = make(NotificationTemplate)
        template_translation = make(
            NotificationTemplateTranslation,
            template=notification_template,
            title="test title",
            body="test sample body",
            language=self.user.language,
        )
        generate_and_send_notification.delay(
            notification_template.pk,
            FaceScanNotificationTypes.SUCCESS,
            self.user.language.pk,
            device_pks,
        )

        mocked_sender.assert_called()
        message = mocked_sender.call_args.kwargs.get("message")
        for device_from_process, device_created in zip(devices, mocked_sender.call_args.args[0]):
            self.assertEqual(device_from_process.id, device_created.id)
        self.assertEqual(message.notification.title, template_translation.title)
        self.assertEqual(message.notification.body, template_translation.body)
        self.assertEqual(
            message.data["link"],
            PUSH_NOTIFICATION_TYPE_TO_CLICK_ACTION_LINK[FaceScanNotificationTypes.SUCCESS],
        )
        self.assertEqual(message.data["type"], "face_scan")
