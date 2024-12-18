from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger

logger = get_task_logger("app")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")
app = Celery("apps")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "send_appointment_reminder_notifications": {
        "task": "apps.routines.tasks.send_reminder_notification_for_appointments",
        "schedule": crontab(minute="0"),  # In every hour.
    },
    "send_reminder_for_daily_questionnaire_notifications": {
        "task": "apps.routines.tasks.send_reminder_for_daily_questionnaire",
        "schedule": crontab(minute="0", hour="15"),  # Everyday at 3pm.
    },
    "send_notification_about_monthly_statistics": {
        "task": "apps.routines.tasks.send_notification_about_monthly_statistics",
        "schedule": crontab(minute="0", hour="13", day_of_month="28-31"),  # Everyday at 1pm.
    },
    "update_sagging_parameter_for_face_scan_analytics": {
        "task": "apps.routines.tasks.update_sagging_parameter_for_face_scan_analytics",
        "schedule": crontab(),
    },
    "update_category": {
        "task": "apps.routines.tasks.update_category",
        "schedule": crontab(),
    },
}

app.conf.timezone = "UTC"
