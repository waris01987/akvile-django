# Generated by Django 3.2.6 on 2021-11-19 12:38

import django.contrib.postgres.fields
from django.db import migrations, models


def create_guilty_pleasures_array_values(apps, schema_editor):
    user_questionnaire = apps.get_model("questionnaire", "UserQuestionnaire")
    for row in user_questionnaire.objects.all():
        row.guilty_pleasures_array = [row.guilty_pleasures]
        row.save(update_fields=["guilty_pleasures_array"])


class Migration(migrations.Migration):

    dependencies = [
        ("questionnaire", "0009_alter_userquestionnaire_exercise_days_a_week"),
    ]

    operations = [
        migrations.AddField(
            model_name="userquestionnaire",
            name="guilty_pleasures_array",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("COFFEE", "COFFEE"),
                        ("ALCOHOL", "ALCOHOL"),
                        ("JUNK_FOOD_AND_SWEETS", "JUNK_FOOD_AND_SWEETS"),
                        ("SMOKING", "SMOKING"),
                        ("SKIPPED", "SKIPPED"),
                    ],
                    max_length=30,
                ),
                default=list,
                null=True,
                size=None,
            ),
        ),
        migrations.RunPython(
            create_guilty_pleasures_array_values, reverse_code=migrations.RunPython.noop
        ),
    ]
