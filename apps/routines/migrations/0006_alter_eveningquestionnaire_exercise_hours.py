# Generated by Django 3.2.6 on 2021-11-15 14:45

from django.db import migrations, models


def change_exercise_hour_values(apps, schema_editor):
    evening_questionnaire = apps.get_model("routines", "EveningQuestionnaire")
    for row in evening_questionnaire.objects.all():
        if row.exercise_hours:
            if row.exercise_hours == "0":
                row.exercise_hours = "ZERO"
            elif row.exercise_hours == "1":
                row.exercise_hours = "ONE_HOUR"
            elif row.exercise_hours == "2":
                row.exercise_hours = "TWO_HOURS"
            else:
                row.exercise_hours = "TWO_PLUS"
            row.save(update_fields=["exercise_hours"])


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0005_alter_eveningquestionnaire_exercise_hours"),
    ]

    operations = [
        migrations.AlterField(
            model_name="eveningquestionnaire",
            name="exercise_hours",
            field=models.CharField(
                choices=[
                    ("ZERO", "ZERO"),
                    ("TWENTY_MIN", "TWENTY_MIN"),
                    ("THIRTY_MIN", "THIRTY_MIN"),
                    ("FORTY_FIVE_MIN", "FORTY_FIVE_MIN"),
                    ("ONE_HOUR", "ONE_HOUR"),
                    ("ONE_AND_A_HALF_HOURS", "ONE_AND_A_HALF_HOURS"),
                    ("TWO_HOURS", "TWO_HOURS"),
                    ("TWO_PLUS", "TWO_PLUS"),
                ],
                max_length=30,
            ),
        ),
        migrations.RunPython(
            change_exercise_hour_values, reverse_code=migrations.RunPython.noop
        ),
    ]