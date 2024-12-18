# Generated by Django 3.2.6 on 2021-08-19 07:15

import ckeditor.fields
import django.contrib.postgres.indexes
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("translations", "0003_alter_translation_language"),
        ("home", "0006_auto_20210818_1432"),
    ]

    operations = [
        migrations.CreateModel(
            name="DashboardElement",
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
                ("image", models.ImageField(upload_to="dashboard_images")),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="DashboardElementTranslation",
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
                    "dashboard_element",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="home.dashboardelement",
                    ),
                ),
                (
                    "language",
                    models.ForeignKey(
                        default="en",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="translations.language",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.DeleteModel(
            name="SkinJourneyTranslation",
        ),
        migrations.AddField(
            model_name="siteconfiguration",
            name="shop_block",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="shop_block",
                to="home.dashboardelement",
            ),
        ),
        migrations.AlterField(
            model_name="siteconfiguration",
            name="skin_journey",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="skin_journey",
                to="home.dashboardelement",
            ),
        ),
        migrations.DeleteModel(
            name="SkinJourney",
        ),
        migrations.AddIndex(
            model_name="dashboardelementtranslation",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["title"], name="home_dashbo_title_f6079c_gin"
            ),
        ),
        migrations.AddConstraint(
            model_name="dashboardelementtranslation",
            constraint=models.UniqueConstraint(
                fields=("language", "dashboard_element"),
                name="One language per dashboard element",
            ),
        ),
    ]