# Generated by Django 3.2.6 on 2021-11-15 15:57

from django.db import migrations, models


def change_exercise_day_a_week_values(apps, schema_editor):
    user_questionnaire = apps.get_model("questionnaire", "UserQuestionnaire")
    for row in user_questionnaire.objects.all():
        if row.exercise_days_a_week == "SKIPPED":
            continue
        if row.exercise_days_a_week == "1":
            row.exercise_days_a_week = "ONE"
        elif row.exercise_days_a_week == "2":
            row.exercise_days_a_week = "TWO"
        elif row.exercise_days_a_week == "3":
            row.exercise_days_a_week = "THREE"
        elif row.exercise_days_a_week == "4":
            row.exercise_days_a_week = "FOUR"
        elif row.exercise_days_a_week == "5":
            row.exercise_days_a_week = "FIVE"
        elif row.exercise_days_a_week == "6":
            row.exercise_days_a_week = "SIX_PLUS"
        elif row.exercise_days_a_week == "7":
            row.exercise_days_a_week = "SIX_PLUS"
        row.save(update_fields=["exercise_days_a_week"])


class Migration(migrations.Migration):

    dependencies = [
        ("questionnaire", "0008_auto_20210928_1042"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userquestionnaire",
            name="exercise_days_a_week",
            field=models.CharField(
                blank=True,
                choices=[
                    ("ZERO", "ZERO"),
                    ("ONE", "ONE"),
                    ("TWO", "TWO"),
                    ("THREE", "THREE"),
                    ("FOUR", "FOUR"),
                    ("FIVE", "FIVE"),
                    ("SIX_PLUS", "SIX_PLUS"),
                    ("SKIPPED", "SKIPPED"),
                ],
                default="",
                max_length=30,
            ),
        ),
        migrations.RunPython(
            change_exercise_day_a_week_values, reverse_code=migrations.RunPython.noop
        ),
    ]
