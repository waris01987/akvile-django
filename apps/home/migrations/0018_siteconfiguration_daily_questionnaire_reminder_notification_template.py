# Generated by Django 3.2.13 on 2022-06-15 08:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0017_siteconfiguration_face_scan_reminder_notification_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="siteconfiguration",
            name="daily_questionnaire_reminder_notification_template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="daily_questionnaire_reminder_notification_template",
                to="home.notificationtemplate",
            ),
        ),
    ]