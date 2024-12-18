# Generated by Django 3.2.4 on 2021-07-13 14:20

import django.contrib.postgres.indexes
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("translations", "0003_alter_translation_language"),
        ("content", "0002_remove_article_uuid"),
    ]

    operations = [
        migrations.CreateModel(
            name="Period",
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
                ("image", models.ImageField(upload_to="period_images")),
                (
                    "period_number_image",
                    models.ImageField(upload_to="period_number_images"),
                ),
                (
                    "unlocks_after_week",
                    models.IntegerField(
                        help_text="Number of a week after which the period unlocks - 0 to 5",
                        validators=[
                            django.core.validators.MaxValueValidator(5),
                            django.core.validators.MinValueValidator(0),
                        ],
                    ),
                ),
                ("ordering", models.PositiveIntegerField()),
            ],
            options={
                "ordering": ["ordering"],
            },
        ),
        migrations.CreateModel(
            name="PeriodTranslation",
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
                ("subtitle", models.CharField(max_length=255)),
                ("description", models.CharField(max_length=255)),
                (
                    "language",
                    models.ForeignKey(
                        default="en",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="translations.language",
                    ),
                ),
                (
                    "period",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="content.period",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="periodtranslation",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["title"], name="content_per_title_d5d847_gin"
            ),
        ),
        migrations.AddConstraint(
            model_name="periodtranslation",
            constraint=models.UniqueConstraint(
                fields=("language", "period"), name="One language per period"
            ),
        ),
    ]