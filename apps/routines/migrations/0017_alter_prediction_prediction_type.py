# Generated by Django 3.2.13 on 2022-06-03 08:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0016_auto_20220601_0658"),
    ]

    operations = [
        migrations.AlterField(
            model_name="prediction",
            name="prediction_type",
            field=models.CharField(
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
                    ("SLEEP_HOURS_LESS_THAN_SEVEN", "SLEEP_HOURS_LESS_THAN_SEVEN"),
                    (
                        "SLEEP_HOURS_GREATER_EQUAL_SEVEN",
                        "SLEEP_HOURS_GREATER_EQUAL_SEVEN",
                    ),
                    ("SLEEP_QUALITY_BAD_OR_MEHHH", "SLEEP_QUALITY_BAD_OR_MEHHH"),
                    ("SLEEP_QUALITY_WELL_OR_LOVE_IT", "SLEEP_QUALITY_WELL_OR_LOVE_IT"),
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
                    ("DAILY_QUESTIONNAIRE_SKIPPED", "DAILY_QUESTIONNAIRE_SKIPPED"),
                ],
                max_length=100,
            ),
        ),
    ]
