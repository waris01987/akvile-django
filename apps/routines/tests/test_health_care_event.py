import datetime
from unittest.mock import patch

from django.db import IntegrityError
from django.urls import reverse
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message
from freezegun import freeze_time
from model_bakery.baker import make
from parameterized import parameterized
from rest_framework import status

from apps.home.models import (
    SiteConfiguration,
    NotificationTemplate,
    NotificationTemplateTranslation,
)
from apps.questionnaire.models import UserQuestionnaire
from apps.routines import HealthCareEventTypes, MedicationTypes, TagCategories
from apps.routines.models import (
    UserTag,
    HealthCareEvent,
)
from apps.routines.tasks import (
    generate_appointment_message,
    send_reminder_notification_for_appointments,
)
from apps.utils.error_codes import Errors
from apps.utils.tests_utils import BaseTestCase


class HealthCareEventTest(BaseTestCase):
    def test_create_medication(self):
        name = "Medicine1"
        duration_in_days = 3
        start_date = datetime.datetime.utcnow().date()
        medication = make(
            HealthCareEvent,
            name=name,
            event_type=HealthCareEventTypes.MEDICATION,
            medication_type=MedicationTypes.PILL,
            start_date=start_date,
            duration=duration_in_days,
            user=self.user,
        )
        self.assertEqual(medication.event_type, HealthCareEventTypes.MEDICATION)
        self.assertEqual(medication.name, name)
        self.assertEqual(medication.start_date, start_date)
        self.assertEqual(medication.duration, duration_in_days)
        self.assertEqual(medication.medication_type, MedicationTypes.PILL)
        self.assertEqual(medication.user, self.user)

    def test_create_medication_event_without_medication_type(self):
        name = "Medicine1"
        duration_in_days = 3
        start_date = datetime.datetime.utcnow().date()
        with self.assertRaises(IntegrityError):
            make(
                HealthCareEvent,
                name=name,
                event_type=HealthCareEventTypes.MEDICATION.value,
                start_date=start_date,
                duration=duration_in_days,
                user=self.user,
            )

    def test_create_medication_without_event_name(self):
        duration_in_days = 3
        start_date = datetime.datetime.utcnow().date()
        with self.assertRaises(IntegrityError):
            make(
                HealthCareEvent,
                event_type=HealthCareEventTypes.MEDICATION,
                medication_type=MedicationTypes.PILL,
                start_date=start_date,
                duration=duration_in_days,
                user=self.user,
            )

    def test_create_medication_without_duration(self):
        name = "Medicine1"
        start_date = datetime.datetime.utcnow().date()
        duration_in_days = 3
        medication_time = datetime.time(4, 45)
        with self.assertRaises(IntegrityError):
            make(
                HealthCareEvent,
                name=name,
                event_type=HealthCareEventTypes.MEDICATION,
                medication_type=MedicationTypes.PILL,
                start_date=start_date,
                duration=duration_in_days,
                time=medication_time,
                user=self.user,
            )

    def test_create_medication_with_time(self):
        name = "Medicine1"
        start_date = datetime.datetime.utcnow().date()
        with self.assertRaises(IntegrityError):
            make(
                HealthCareEvent,
                name=name,
                event_type=HealthCareEventTypes.MEDICATION,
                medication_type=MedicationTypes.PILL,
                start_date=start_date,
                user=self.user,
            )

    def test_create_appointment(self):
        name = "Appointment1"
        appointment_time = datetime.time(4, 45)
        start_date = datetime.datetime.utcnow().date()
        appointment = make(
            HealthCareEvent,
            name=name,
            event_type=HealthCareEventTypes.APPOINTMENT,
            start_date=start_date,
            time=appointment_time,
            user=self.user,
        )
        self.assertEqual(appointment.event_type, HealthCareEventTypes.APPOINTMENT)
        self.assertEqual(appointment.name, name)
        self.assertEqual(appointment.start_date, start_date)
        self.assertEqual(appointment.time, appointment_time)
        self.assertEqual(appointment.user, self.user)

    def test_create_appointment_without_name(self):
        appointment_time = datetime.time(4, 45)
        start_date = datetime.datetime.utcnow().date()
        with self.assertRaises(IntegrityError):
            make(
                HealthCareEvent,
                event_type=HealthCareEventTypes.APPOINTMENT,
                start_date=start_date,
                time=appointment_time,
                user=self.user,
            )

    def test_create_appointment_without_time(self):
        name = "Appointment1"
        start_date = datetime.datetime.utcnow().date()
        with self.assertRaises(IntegrityError):
            make(
                HealthCareEvent,
                name=name,
                event_type=HealthCareEventTypes.APPOINTMENT,
                start_date=start_date,
                user=self.user,
            )

    def test_create_appointment_with_duration(self):
        name = "Appointment1"
        appointment_time = datetime.time(4, 45)
        start_date = datetime.datetime.utcnow().date()
        with self.assertRaises(IntegrityError):
            make(
                HealthCareEvent,
                name=name,
                event_type=HealthCareEventTypes.APPOINTMENT,
                start_date=start_date,
                time=appointment_time,
                duration=2,
                user=self.user,
            )

    def test_create_appointment_with_medication_type(self):
        name = "Appointment1"
        appointment_time = datetime.time(4, 45)
        start_date = datetime.datetime.utcnow().date()
        with self.assertRaises(IntegrityError):
            make(
                HealthCareEvent,
                name=name,
                event_type=HealthCareEventTypes.APPOINTMENT,
                medication_type=MedicationTypes.PILL,
                start_date=start_date,
                time=appointment_time,
                user=self.user,
            )

    def test_create_menstruation(self):
        duration_in_days = 6
        start_date = datetime.datetime.utcnow().date()
        appointment = make(
            HealthCareEvent,
            event_type=HealthCareEventTypes.MENSTRUATION,
            start_date=start_date,
            duration=duration_in_days,
            user=self.user,
        )
        self.assertEqual(appointment.event_type, HealthCareEventTypes.MENSTRUATION)
        self.assertEqual(appointment.start_date, start_date)
        self.assertEqual(appointment.duration, duration_in_days)
        self.assertEqual(appointment.user, self.user)

    def test_create_menstruation_with_name(self):
        duration_in_days = 6
        start_date = datetime.datetime.utcnow().date()
        with self.assertRaises(IntegrityError):
            make(
                HealthCareEvent,
                name="Invalid Menstruation Event",
                event_type=HealthCareEventTypes.MENSTRUATION,
                start_date=start_date,
                duration=duration_in_days,
                user=self.user,
            )

    def test_create_menstruation_with_medication_type(self):
        duration_in_days = 6
        start_date = datetime.datetime.utcnow().date()
        with self.assertRaises(IntegrityError):
            make(
                HealthCareEvent,
                medication_type=MedicationTypes.PILL,
                event_type=HealthCareEventTypes.MENSTRUATION,
                start_date=start_date,
                duration=duration_in_days,
                user=self.user,
            )

    def test_create_menstruation_with_time(self):
        duration_in_days = 6
        start_date = datetime.datetime.utcnow().date()
        with self.assertRaises(IntegrityError):
            make(
                HealthCareEvent,
                event_type=HealthCareEventTypes.MENSTRUATION,
                start_date=start_date,
                duration=duration_in_days,
                time=datetime.time(4, 0),
                user=self.user,
            )

    def test_create_menstruation_without_duration(self):
        start_date = datetime.datetime.utcnow().date()
        with self.assertRaises(IntegrityError):
            make(
                HealthCareEvent,
                event_type=HealthCareEventTypes.MENSTRUATION,
                start_date=start_date,
                user=self.user,
            )


class AppointmentEventTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.appointment_tag = make(UserTag, name="after meal", category=TagCategories.APPOINTMENT)
        self.appointment_template = make(NotificationTemplate, name="Appointment Reminder Template")
        self.appointment_template_translation = make(
            NotificationTemplateTranslation,
            template=self.appointment_template,
            language=self.user.language,
            title="Appointment Reminder",
            body="You have appointment at",
        )

        self.site_config = SiteConfiguration.get_solo()
        self.site_config.appointment_reminder_notification_template = self.appointment_template
        self.site_config.save()

    def test_appointment_event_list(self):
        appointment_events = make(
            HealthCareEvent,
            user=self.user,
            name="Appointment Event1",
            event_type=HealthCareEventTypes.APPOINTMENT,
            time=datetime.time(7, 0),
            _quantity=2,
        )
        for ap_event in appointment_events:
            ap_event.event_tags.set([self.appointment_tag])
            ap_event.save()
        url = reverse("appointment-events-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        events_from_response = response.json()["results"]
        for res_event, event in zip(events_from_response, appointment_events):
            self.assertEqual(event.id, res_event["id"])
            self.assertEqual(event.name, res_event["name"])
            self.assertEqual(event.start_date.strftime("%Y-%m-%d"), res_event["start_date"])
            self.assertEqual(event.time.strftime("%H:%M:%S"), res_event["time"])
            self.assertEqual(
                event.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                res_event["created_at"],
            )
            self.assertEqual([self.appointment_tag.name], res_event["appointment_tags"])

    def test_create_valid_appointment_event(self):
        self.query_limits["ANY POST REQUEST"] = 6
        start_date = datetime.datetime.utcnow().date()
        url = reverse("appointment-events-list")
        data = {
            "name": "Appointment Event1",
            "start_date": start_date,
            "time": datetime.time(7, 0),
            "event_tags": [self.appointment_tag.id],
            "remind_me": False,
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        appointment_event = HealthCareEvent.objects.get(user=self.user, event_type=HealthCareEventTypes.APPOINTMENT)
        events_from_response = response.json()
        self.assertEqual(appointment_event.id, events_from_response["id"])
        self.assertEqual(appointment_event.name, events_from_response["name"])
        self.assertEqual(appointment_event.remind_me, events_from_response["remind_me"])
        self.assertEqual(
            appointment_event.start_date.strftime("%Y-%m-%d"),
            events_from_response["start_date"],
        )
        self.assertEqual(appointment_event.time.strftime("%H:%M:%S"), events_from_response["time"])
        self.assertEqual(
            appointment_event.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            events_from_response["created_at"],
        )
        self.assertEqual(
            [self.appointment_tag.id],
            list(appointment_event.event_tags.values_list("id", flat=True)),
        )

    def test_retrieve_appointment_event(self):
        appointment_event = make(
            HealthCareEvent,
            user=self.user,
            name="Appointment Event1",
            event_type=HealthCareEventTypes.APPOINTMENT,
            time=datetime.time(7, 0),
        )
        appointment_event.event_tags.set([self.appointment_tag])
        appointment_event.save()
        url = reverse("appointment-events-detail", args=[appointment_event.id])
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        events_from_response = response.json()
        self.assertEqual(appointment_event.id, events_from_response["id"])
        self.assertEqual(appointment_event.name, events_from_response["name"])
        self.assertEqual(appointment_event.remind_me, events_from_response["remind_me"])
        self.assertEqual(
            appointment_event.start_date.strftime("%Y-%m-%d"),
            events_from_response["start_date"],
        )
        self.assertEqual(appointment_event.time.strftime("%H:%M:%S"), events_from_response["time"])
        self.assertEqual(
            appointment_event.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            events_from_response["created_at"],
        )
        self.assertEqual([self.appointment_tag.name], events_from_response["appointment_tags"])

    def test_delete_appointment_event(self):
        appointment_events = make(
            HealthCareEvent,
            user=self.user,
            name="Medication Event",
            event_type=HealthCareEventTypes.APPOINTMENT,
            time=datetime.time(7, 0),
        )
        appointment_events.event_tags.set([self.appointment_tag])
        appointment_events.save()
        url = reverse("appointment-events-detail", args=[appointment_events.id])
        response = self.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            HealthCareEvent.objects.filter(user=self.user, event_type=HealthCareEventTypes.APPOINTMENT).exists()
        )

    def test_create_appointment_event_without_name(self):
        self.query_limits["ANY POST REQUEST"] = 6
        start_date = datetime.datetime.utcnow().date()
        url = reverse("appointment-events-list")
        data = {
            "start_date": start_date,
            "time": datetime.time(7, 30),
            "event_tags": [self.appointment_tag.id],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            Errors.INVALID_APPOINTMENT_EVENT.value,
        )

    def test_create_appointment_event_without_time(self):
        self.query_limits["ANY POST REQUEST"] = 6
        start_date = datetime.datetime.utcnow().date()
        url = reverse("appointment-events-list")
        data = {
            "name": "Invalid Appointment2",
            "start_date": start_date,
            "event_tags": [self.appointment_tag.id],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            Errors.INVALID_APPOINTMENT_EVENT.value,
        )

    def test_create_appointment_event_with_invalid_tags(self):
        invalid_tag_id = 100
        self.query_limits["ANY POST REQUEST"] = 6
        start_date = datetime.datetime.utcnow().date()
        url = reverse("appointment-events-list")
        data = {
            "name": "Invalid Appointment3",
            "start_date": start_date,
            "time": datetime.time(7, 0),
            "event_tags": [invalid_tag_id],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["event_tags"][0],
            f'Invalid pk "{invalid_tag_id}" - object does not exist.',
        )

    def test_update_appointment_event(self):
        appointment_event = make(
            HealthCareEvent,
            user=self.user,
            name="Appointment Event1",
            event_type=HealthCareEventTypes.APPOINTMENT,
            time=datetime.time(7, 0),
        )
        appointment_event.event_tags.set([self.appointment_tag])
        appointment_event.save()
        url = reverse("appointment-events-detail", args=[appointment_event.id])
        data = {
            "start_date": datetime.date(2022, 6, 2),
            "time": datetime.time(7, 30),
            "remind_me": False,
        }
        response = self.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        events_from_response = response.json()
        appointment_event.refresh_from_db()
        self.assertEqual(appointment_event.id, events_from_response["id"])
        self.assertEqual(appointment_event.name, events_from_response["name"])
        self.assertEqual(appointment_event.remind_me, events_from_response["remind_me"])
        self.assertFalse(appointment_event.remind_me)
        self.assertEqual(
            appointment_event.start_date.strftime("%Y-%m-%d"),
            events_from_response["start_date"],
        )
        self.assertEqual(appointment_event.time.strftime("%H:%M:%S"), events_from_response["time"])
        self.assertEqual(
            appointment_event.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            events_from_response["created_at"],
        )
        self.assertEqual([self.appointment_tag.name], events_from_response["appointment_tags"])

    def test_create_multiple_appointment_events_at_the_same_datetime(self):
        self.query_limits["ANY POST REQUEST"] = 6
        start_date = datetime.datetime.utcnow().date()
        time = datetime.time(7, 30)
        make(
            HealthCareEvent,
            event_type=HealthCareEventTypes.APPOINTMENT,
            user=self.user,
            name="Appointment1",
            start_date=start_date,
            time=time,
        )
        url = reverse("appointment-events-list")
        data = {
            "name": "Appointment2",
            "start_date": start_date,
            "time": time,
            "event_tags": [self.appointment_tag.id],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            Errors.APPOINTMENT_EVENT_ALREADY_EXISTS_FOR_SAME_DATE_TIME.value,
        )

    def test_generate_appointment_message(self):
        appointment_event = make(
            HealthCareEvent,
            user=self.user,
            name="Appointment Event1",
            event_type=HealthCareEventTypes.APPOINTMENT,
            time=datetime.time(7, 0),
        )
        notification_body = (
            f"{self.appointment_template_translation.body} {appointment_event.start_date} {appointment_event.time}."
        )
        generated_message = generate_appointment_message(self.appointment_template_translation, appointment_event)
        self.assertIsInstance(generated_message, Message)
        self.assertEqual(
            generated_message.notification.title,
            self.appointment_template_translation.title,
        )
        self.assertEqual(generated_message.notification.body, notification_body)

    @parameterized.expand(
        [
            ["2022-06-01", "07:00:00", True],
            ["2022-06-01", "07:00:00", False],
            ["2022-06-02", "06:00:00", True],
            ["2022-06-02", "06:00:00", False],
        ]
    )
    @patch("apps.routines.tasks.send_push_notifications")
    @freeze_time("2022-06-01 06:00:00")
    def test_appointment_reminder_task_with_valid_events_timeline(
        self, start_date, time, remind_me, mocked_send_push_notifications
    ):
        make(UserQuestionnaire, user=self.user)
        event = make(
            HealthCareEvent,
            user=self.user,
            name="Sample Appointment",
            event_type=HealthCareEventTypes.APPOINTMENT,
            start_date=start_date,
            time=time,
            remind_me=remind_me,
        )
        make(FCMDevice, user=self.user)
        generated_message = generate_appointment_message(self.appointment_template_translation, event)
        send_reminder_notification_for_appointments()
        user_devices = FCMDevice.objects.filter(user=self.user)
        if remind_me:
            self.assertTrue(mocked_send_push_notifications.called)
            self.assertEqual(
                mocked_send_push_notifications.call_args.args[0].count(),
                user_devices.count(),
            )
            self.assertEqual(
                mocked_send_push_notifications.call_args.args[0].first(),
                user_devices.first(),
            )
            message = mocked_send_push_notifications.call_args.kwargs["message"]
            self.assertEqual(message.notification.title, generated_message.notification.title)
            self.assertEqual(message.notification.body, generated_message.notification.body)
        else:
            self.assertFalse(mocked_send_push_notifications.called)

    @parameterized.expand(
        [
            ["2022-06-01", "07:00:00", True],
            ["2022-06-01", "07:00:00", False],
            ["2022-06-02", "06:00:00", True],
            ["2022-06-02", "06:00:00", False],
        ]
    )
    @patch("apps.routines.tasks.send_push_notifications")
    @freeze_time("2022-06-01 06:00:00")
    def test_appointment_reminder_task_with_valid_events_timeline_no_questionnaire(
        self, start_date, time, remind_me, mocked_send_push_notifications
    ):
        make(
            HealthCareEvent,
            user=self.user,
            name="Sample Appointment",
            event_type=HealthCareEventTypes.APPOINTMENT,
            start_date=start_date,
            time=time,
            remind_me=remind_me,
        )
        make(FCMDevice, user=self.user)
        send_reminder_notification_for_appointments()
        self.assertFalse(mocked_send_push_notifications.called)

    @parameterized.expand(
        [
            ["2022-06-01", "06:30:00"],
            ["2022-06-01", "09:30:00"],
            ["2022-06-02", "04:00:00"],
            ["2022-06-02", "10:00:00"],
            ["2022-06-03", "06:30:00"],
        ]
    )
    @patch("apps.routines.tasks.send_push_notifications")
    @freeze_time("2022-06-01 6:00:00")
    def test_appointment_reminder_task_with_invalid_event_timeline(
        self, start_date, time, mocked_send_push_notifications
    ):
        make(
            HealthCareEvent,
            user=self.user,
            name="Sample Appointment",
            event_type=HealthCareEventTypes.APPOINTMENT,
            start_date=start_date,
            time=time,
        )
        make(FCMDevice, user=self.user)
        send_reminder_notification_for_appointments()
        self.assertFalse(mocked_send_push_notifications.called)

    @parameterized.expand(
        [
            ["2022-06-01", "07:00:00"],
            ["2022-06-02", "06:00:00"],
        ]
    )
    @patch("apps.routines.tasks.send_push_notifications")
    @freeze_time("2022-06-01 06:00:00")
    def test_appointment_reminder_task_with_valid_events_timeline_and_no_notification_templates(
        self, start_date, time, mocked_send_push_notifications
    ):
        make(
            HealthCareEvent,
            user=self.user,
            name="Sample Appointment",
            event_type=HealthCareEventTypes.APPOINTMENT,
            start_date=start_date,
            time=time,
        )
        make(FCMDevice, user=self.user)
        self.site_config.appointment_reminder_notification_template = None
        self.site_config.save()
        send_reminder_notification_for_appointments()
        self.assertFalse(mocked_send_push_notifications.called)

    @patch("apps.routines.tasks.send_push_notifications")
    def test_appointment_reminder_task_with_specified_appointment_events(self, mocked_send_push_notifications):
        make(UserQuestionnaire, user=self.user)
        event = make(
            HealthCareEvent,
            user=self.user,
            name="Sample Appointment",
            event_type=HealthCareEventTypes.APPOINTMENT,
            start_date="2022-06-01",
            time="07:00:00",
        )
        make(FCMDevice, user=self.user)
        generated_message = generate_appointment_message(self.appointment_template_translation, event)
        send_reminder_notification_for_appointments([event.id])
        user_devices = FCMDevice.objects.filter(user=self.user)
        self.assertTrue(mocked_send_push_notifications.called)
        self.assertEqual(
            mocked_send_push_notifications.call_args.args[0].count(),
            user_devices.count(),
        )
        self.assertEqual(
            mocked_send_push_notifications.call_args.args[0].first(),
            user_devices.first(),
        )
        message = mocked_send_push_notifications.call_args.kwargs["message"]
        self.assertEqual(message.notification.title, generated_message.notification.title)
        self.assertEqual(message.notification.body, generated_message.notification.body)

    @patch("apps.routines.tasks.send_push_notifications")
    def test_appointment_reminder_task_with_specified_appointment_events_no_questionnaire(
        self, mocked_send_push_notifications
    ):
        event = make(
            HealthCareEvent,
            user=self.user,
            name="Sample Appointment",
            event_type=HealthCareEventTypes.APPOINTMENT,
            start_date="2022-06-01",
            time="07:00:00",
        )
        make(FCMDevice, user=self.user)
        send_reminder_notification_for_appointments([event.id])
        self.assertFalse(mocked_send_push_notifications.called)

    @patch("apps.routines.tasks.send_push_notifications")
    def test_appointment_reminder_task_with_specified_appointment_events_but_negative_reminder_settings(
        self, mocked_send_push_notifications
    ):
        make(
            HealthCareEvent,
            user=self.user,
            name="Sample Appointment",
            event_type=HealthCareEventTypes.APPOINTMENT,
            start_date="2022-06-01",
            time="07:00:00",
            remind_me=False,
        )
        make(FCMDevice, user=self.user)
        self.assertFalse(mocked_send_push_notifications.called)


class MedicationEventTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.medication_tag = make(UserTag, name="before meal", category=TagCategories.MEDICATION)

    def test_medication_event_list(self):
        medication_events = make(
            HealthCareEvent,
            user=self.user,
            name="Medication Event",
            medication_type=MedicationTypes.PILL,
            event_type=HealthCareEventTypes.MEDICATION,
            duration=2,
            _quantity=2,
        )
        for med_event in medication_events:
            med_event.event_tags.set([self.medication_tag])
            med_event.save()
        url = reverse("medication-events-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        events_from_response = response.json()["results"]
        for res_event, event in zip(events_from_response, medication_events):
            self.assertEqual(event.id, res_event["id"])
            self.assertEqual(event.name, res_event["name"])
            self.assertEqual(event.medication_type, res_event["medication_type"])
            self.assertEqual(event.start_date.strftime("%Y-%m-%d"), res_event["start_date"])
            self.assertEqual(event.duration, res_event["duration"])
            self.assertEqual(
                event.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                res_event["created_at"],
            )
            self.assertEqual([self.medication_tag.name], res_event["medication_tags"])

    def test_create_valid_medication_event(self):
        self.query_limits["ANY POST REQUEST"] = 6
        start_date = datetime.datetime.utcnow().date()
        url = reverse("medication-events-list")
        data = {
            "name": "Medication1",
            "medication_type": MedicationTypes.PILL,
            "start_date": start_date,
            "duration": 3,
            "event_tags": [self.medication_tag.id],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        medication_event = HealthCareEvent.objects.get(user=self.user, event_type=HealthCareEventTypes.MEDICATION)
        events_from_response = response.json()
        self.assertEqual(medication_event.id, events_from_response["id"])
        self.assertEqual(medication_event.name, events_from_response["name"])
        self.assertEqual(medication_event.medication_type, events_from_response["medication_type"])
        self.assertEqual(
            medication_event.start_date.strftime("%Y-%m-%d"),
            events_from_response["start_date"],
        )
        self.assertEqual(medication_event.duration, events_from_response["duration"])
        self.assertEqual(
            medication_event.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            events_from_response["created_at"],
        )
        self.assertEqual(
            [self.medication_tag.id],
            list(medication_event.event_tags.values_list("id", flat=True)),
        )

    def test_retrieve_medication_event(self):
        medication_event = make(
            HealthCareEvent,
            user=self.user,
            name="Medication Event",
            medication_type=MedicationTypes.PILL,
            event_type=HealthCareEventTypes.MEDICATION,
            duration=2,
        )
        medication_event.event_tags.set([self.medication_tag])
        medication_event.save()
        url = reverse("medication-events-detail", args=[medication_event.id])
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        events_from_response = response.json()
        self.assertEqual(medication_event.id, events_from_response["id"])
        self.assertEqual(medication_event.name, events_from_response["name"])
        self.assertEqual(medication_event.medication_type, events_from_response["medication_type"])
        self.assertEqual(
            medication_event.start_date.strftime("%Y-%m-%d"),
            events_from_response["start_date"],
        )
        self.assertEqual(medication_event.duration, events_from_response["duration"])
        self.assertEqual(
            medication_event.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            events_from_response["created_at"],
        )
        self.assertEqual([self.medication_tag.name], events_from_response["medication_tags"])

    def test_delete_medication_event(self):
        medication_event = make(
            HealthCareEvent,
            user=self.user,
            name="Medication Event",
            medication_type=MedicationTypes.PILL,
            event_type=HealthCareEventTypes.MEDICATION,
            duration=2,
        )
        medication_event.event_tags.set([self.medication_tag])
        medication_event.save()
        url = reverse("medication-events-detail", args=[medication_event.id])
        response = self.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            HealthCareEvent.objects.filter(user=self.user, event_type=HealthCareEventTypes.MEDICATION).exists()
        )

    def test_create_medication_event_without_duration(self):
        self.query_limits["ANY POST REQUEST"] = 6
        start_date = datetime.datetime.utcnow().date()
        url = reverse("medication-events-list")
        data = {
            "name": "Invalid medication1",
            "medication_type": MedicationTypes.SKIN,
            "start_date": start_date,
            "event_tags": [self.medication_tag.id],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            Errors.INVALID_MEDICATION_EVENT.value,
        )

    def test_create_medication_event_without_name(self):
        self.query_limits["ANY POST REQUEST"] = 6
        start_date = datetime.datetime.utcnow().date()
        url = reverse("medication-events-list")
        data = {
            "medication_type": MedicationTypes.SKIN,
            "duration": 2,
            "start_date": start_date,
            "event_tags": [self.medication_tag.id],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            Errors.INVALID_MEDICATION_EVENT.value,
        )

    def test_create_medication_event_without_medication_type(self):
        self.query_limits["ANY POST REQUEST"] = 6
        start_date = datetime.datetime.utcnow().date()
        url = reverse("medication-events-list")
        data = {
            "name": "Invalid medication3",
            "duration": 3,
            "start_date": start_date,
            "event_tags": [self.medication_tag.id],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            Errors.INVALID_MEDICATION_EVENT.value,
        )

    def test_create_medication_event_with_invalid_tags(self):
        invalid_tag_id = 100
        self.query_limits["ANY POST REQUEST"] = 6
        start_date = datetime.datetime.utcnow().date()
        url = reverse("medication-events-list")
        data = {
            "name": "Invalid Medication2",
            "medication_type": MedicationTypes.PILL,
            "start_date": start_date,
            "duration": 3,
            "event_tags": [invalid_tag_id],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["event_tags"][0],
            f'Invalid pk "{invalid_tag_id}" - object does not exist.',
        )

    def test_update_medication_event(self):
        medication_event = make(
            HealthCareEvent,
            user=self.user,
            name="Medication Event",
            medication_type=MedicationTypes.PILL,
            event_type=HealthCareEventTypes.MEDICATION,
            duration=2,
        )
        medication_event.event_tags.set([self.medication_tag])
        medication_event.save()
        data = {"duration": 4}
        url = reverse("medication-events-detail", args=[medication_event.id])
        response = self.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        events_from_response = response.json()
        self.assertEqual(medication_event.id, events_from_response["id"])
        self.assertEqual(medication_event.name, events_from_response["name"])
        self.assertEqual(medication_event.medication_type, events_from_response["medication_type"])
        self.assertEqual(
            medication_event.start_date.strftime("%Y-%m-%d"),
            events_from_response["start_date"],
        )
        self.assertEqual(data["duration"], events_from_response["duration"])
        self.assertEqual(
            medication_event.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            events_from_response["created_at"],
        )
        self.assertEqual([self.medication_tag.name], events_from_response["medication_tags"])


class MenstruationEventTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.menstruation_tag = make(UserTag, name="before meal", category=TagCategories.MENSTRUATION)

    def test_menstruation_event_list(self):
        menstruation_events = make(
            HealthCareEvent,
            user=self.user,
            event_type=HealthCareEventTypes.MENSTRUATION,
            duration=2,
            _quantity=2,
        )
        for mens_event in menstruation_events:
            mens_event.event_tags.set([self.menstruation_tag])
            mens_event.save()
        url = reverse("menstruation-events-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        events_from_response = response.json()["results"]
        for res_event, event in zip(events_from_response, menstruation_events):
            self.assertEqual(event.id, res_event["id"])
            self.assertEqual(event.start_date.strftime("%Y-%m-%d"), res_event["start_date"])
            self.assertEqual(event.duration, res_event["duration"])
            self.assertEqual(
                event.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                res_event["created_at"],
            )
            self.assertEqual([self.menstruation_tag.name], res_event["menstruation_tags"])

    def test_create_valid_menstruation_event(self):
        self.query_limits["ANY POST REQUEST"] = 6
        start_date = datetime.datetime.utcnow().date()
        url = reverse("menstruation-events-list")
        data = {
            "start_date": start_date,
            "duration": 3,
            "event_tags": [self.menstruation_tag.id],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        menstruation_event = HealthCareEvent.objects.get(user=self.user, event_type=HealthCareEventTypes.MENSTRUATION)
        events_from_response = response.json()
        self.assertEqual(menstruation_event.id, events_from_response["id"])
        self.assertEqual(
            menstruation_event.start_date.strftime("%Y-%m-%d"),
            events_from_response["start_date"],
        )
        self.assertEqual(menstruation_event.duration, events_from_response["duration"])
        self.assertEqual(
            menstruation_event.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            events_from_response["created_at"],
        )
        self.assertEqual(
            [self.menstruation_tag.id],
            list(menstruation_event.event_tags.values_list("id", flat=True)),
        )

    def test_retrieve_menstruation_event(self):
        menstruation_event = make(
            HealthCareEvent,
            user=self.user,
            event_type=HealthCareEventTypes.MENSTRUATION,
            duration=3,
        )
        menstruation_event.event_tags.set([self.menstruation_tag])
        menstruation_event.save()
        url = reverse("menstruation-events-detail", args=[menstruation_event.id])
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        events_from_response = response.json()
        self.assertEqual(menstruation_event.id, events_from_response["id"])
        self.assertEqual(
            menstruation_event.start_date.strftime("%Y-%m-%d"),
            events_from_response["start_date"],
        )
        self.assertEqual(menstruation_event.duration, events_from_response["duration"])
        self.assertEqual(
            menstruation_event.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            events_from_response["created_at"],
        )
        self.assertEqual([self.menstruation_tag.name], events_from_response["menstruation_tags"])

    def test_delete_menstruation_event(self):
        menstruation_events = make(
            HealthCareEvent,
            user=self.user,
            event_type=HealthCareEventTypes.MENSTRUATION,
            duration=2,
        )
        menstruation_events.event_tags.set([self.menstruation_tag])
        menstruation_events.save()
        url = reverse("menstruation-events-detail", args=[menstruation_events.id])
        response = self.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            HealthCareEvent.objects.filter(user=self.user, event_type=HealthCareEventTypes.MENSTRUATION).exists()
        )

    def test_create_menstruation_event_without_duration(self):
        self.query_limits["ANY POST REQUEST"] = 6
        start_date = datetime.datetime.utcnow().date()
        url = reverse("menstruation-events-list")
        data = {
            "start_date": start_date,
            "event_tags": [self.menstruation_tag.id],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            Errors.INVALID_MENSTRUATION_EVENT.value,
        )

    def test_create_menstruation_event_with_invalid_tags(self):
        invalid_tag_id = 100
        self.query_limits["ANY POST REQUEST"] = 6
        start_date = datetime.datetime.utcnow().date()
        url = reverse("menstruation-events-list")
        data = {
            "start_date": start_date,
            "duration": 3,
            "event_tags": [invalid_tag_id],
        }

        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["event_tags"][0],
            f'Invalid pk "{invalid_tag_id}" - object does not exist.',
        )

    def test_update_menstruation_event(self):
        menstruation_event = make(
            HealthCareEvent,
            user=self.user,
            event_type=HealthCareEventTypes.MENSTRUATION,
            duration=2,
        )
        menstruation_event.event_tags.set([self.menstruation_tag])
        menstruation_event.save()
        data = {"duration": 4}
        url = reverse("menstruation-events-detail", args=[menstruation_event.id])
        response = self.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        events_from_response = response.json()
        self.assertEqual(menstruation_event.id, events_from_response["id"])
        self.assertEqual(
            menstruation_event.start_date.strftime("%Y-%m-%d"),
            events_from_response["start_date"],
        )
        self.assertEqual(data["duration"], events_from_response["duration"])
        self.assertEqual(
            menstruation_event.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            events_from_response["created_at"],
        )
        self.assertEqual([self.menstruation_tag.name], events_from_response["menstruation_tags"])
