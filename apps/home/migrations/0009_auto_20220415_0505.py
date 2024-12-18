# Generated by Django 3.2.12 on 2022-04-15 05:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("translations", "0003_alter_translation_language"),
        ("home", "0008_rename_progress_dashboardorder_recipes"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationTemplate",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="NotificationTemplateTranslation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField()),
                (
                    "language",
                    models.ForeignKey(
                        default="en",
                        on_delete=django.db.models.deletion.SET_DEFAULT,
                        to="translations.language",
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="home.notificationtemplate",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="siteconfiguration",
            name="face_analysis_completed_notification_template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="face_analysis_completed_notification_template",
                to="home.notificationtemplate",
            ),
        ),
        migrations.AddField(
            model_name="siteconfiguration",
            name="invalid_face_scan_notification_template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="invalid_face_scan_notification_template",
                to="home.notificationtemplate",
            ),
        ),
        migrations.AddConstraint(
            model_name="notificationtemplatetranslation",
            constraint=models.UniqueConstraint(
                fields=("template", "language"), name="One template per language"
            ),
        ),
    ]