# Generated by Django 3.2.13 on 2022-05-20 09:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("routines", "0014_facescancomment"),
    ]

    operations = [
        migrations.CreateModel(
            name="Prediction",
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
                    "prediction_type",
                    models.CharField(
                        choices=[
                            ("NO_PREDICTION", "NO_PREDICTION"),
                            ("ROUTINE_SKIPPED", "ROUTINE_SKIPPED"),
                            ("ROUTINE_MISSED", "ROUTINE_MISSED"),
                            ("ROUTINE_DONE", "ROUTINE_DONE"),
                            ("SKIN_TODAY_BAD_OR_MEHHH", "SKIN_TODAY_BAD_OR_MEHHH"),
                            ("SKIN_TODAY_LOVE_IT", "SKIN_TODAY_LOVE_IT"),
                            ("SKIN_TODAY_WELL", "SKIN_TODAY_WELL"),
                            ("SKIN_FEELING_SENSITIVE", "SKIN_FEELING_SENSITIVE"),
                            ("SKIN_FEELING_GREASY", "SKIN_FEELING_GREASY"),
                            ("SKIN_FEELING_NORMAL", "SKIN_FEELING_NORMAL"),
                            ("SKIN_FEELING_DEHYDRATED", "SKIN_FEELING_DEHYDRATED"),
                            (
                                "SLEEP_HOURS_LESS_THAN_SEVEN",
                                "SLEEP_HOURS_LESS_THAN_SEVEN",
                            ),
                            (
                                "SLEEP_HOURS_GREATER_EQUAL_SEVEN",
                                "SLEEP_HOURS_GREATER_EQUAL_SEVEN",
                            ),
                            (
                                "SLEEP_QUALITY_BAD_OR_MEHHH",
                                "SLEEP_QUALITY_BAD_OR_MEHHH",
                            ),
                            (
                                "SLEEP_QUALITY_WELL_OR_LOVE_IT",
                                "SLEEP_QUALITY_WELL_OR_LOVE_IT",
                            ),
                            ("EXERCISE_HOURS_BAD", "EXERCISE_HOURS_BAD"),
                            ("EXERCISE_HOURS_GOOD", "EXERCISE_HOURS_GOOD"),
                            ("EXERCISE_HOURS_PERFECT", "EXERCISE_HOURS_PERFECT"),
                            ("STRESS_EXTREME", "STRESS_EXTREME"),
                            ("STRESS_MODERATE", "STRESS_MODERATE"),
                            ("STRESS_RELAXED", "STRESS_RELAXED"),
                            ("DIET_BALANCED", "DIET_BALANCED"),
                            (
                                "DIET_UNBALANCED_or_MILDLY_BALANCED",
                                "DIET_UNBALANCED_or_MILDLY_BALANCED",
                            ),
                            ("WATER_INTAKE_ZERO_OR_ONE", "WATER_INTAKE_ZERO_OR_ONE"),
                            ("WATER_INTAKE_TWO_OR_THREE", "WATER_INTAKE_TWO_OR_THREE"),
                            (
                                "LIFE_HAPPENED_COFFEE_OR_ALCOHOL_OR_JUNK_FOOD",
                                "LIFE_HAPPENED_COFFEE_OR_ALCOHOL_OR_JUNK_FOOD",
                            ),
                            ("MENSTRUATION_FOLLICULAR", "MENSTRUATION_FOLLICULAR"),
                            ("MENSTRUATION_DURING", "MENSTRUATION_DURING"),
                            ("MENSTRUATION_OVULATION", "MENSTRUATION_OVULATION"),
                            ("MENSTRUATION_LUTEAL", "MENSTRUATION_LUTEAL"),
                        ],
                        max_length=100,
                    ),
                ),
                ("date", models.DateField(help_text="date for the prediction")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="predictions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-date"],
            },
        ),
        migrations.AddConstraint(
            model_name="prediction",
            constraint=models.UniqueConstraint(
                fields=("user", "date"), name="One prediction per day"
            ),
        ),
    ]