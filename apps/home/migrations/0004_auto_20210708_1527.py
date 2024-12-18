# Generated by Django 3.2.4 on 2021-07-08 15:27

import ckeditor.fields
import django.contrib.postgres.indexes
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("translations", "0003_alter_translation_language"),
        ("home", "0003_alter_emailtemplatetranslation_language"),
    ]

    operations = [
        migrations.CreateModel(
            name="AboutAndNoticeSection",
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
                (
                    "name",
                    models.CharField(
                        help_text="Technical name.", max_length=255, unique=True
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="AboutAndNoticeSectionTranslation",
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
                ("title", models.TextField()),
                ("content", ckeditor.fields.RichTextField()),
                (
                    "language",
                    models.ForeignKey(
                        default="en",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="translations.language",
                    ),
                ),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="home.aboutandnoticesection",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="aboutandnoticesectiontranslation",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["title"], name="home_abouta_title_48a9a5_gin"
            ),
        ),
        migrations.AddConstraint(
            model_name="aboutandnoticesectiontranslation",
            constraint=models.UniqueConstraint(
                fields=("language", "section"), name="One language per section"
            ),
        ),
    ]
