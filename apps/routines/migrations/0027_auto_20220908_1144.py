# Generated by Django 3.2.15 on 2022-09-08 11:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0026_auto_20220905_1104"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dailyquestionnaire",
            name="exercise_hours",
            field=models.CharField(
                choices=[
                    ("TWO_PLUS", "TWO_PLUS"),
                    ("TWO_HOURS", "TWO_HOURS"),
                    ("ONE_AND_A_HALF_HOURS", "ONE_AND_A_HALF_HOURS"),
                    ("ONE_HOUR", "ONE_HOUR"),
                    ("FORTY_FIVE_MIN", "FORTY_FIVE_MIN"),
                    ("THIRTY_MIN", "THIRTY_MIN"),
                    ("TWENTY_MIN", "TWENTY_MIN"),
                    ("ZERO", "ZERO"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="dailyquestionnaire",
            name="feeling_today",
            field=models.CharField(
                choices=[
                    ("LOVE_IT", "LOVE_IT"),
                    ("WELL", "WELL"),
                    ("MEHHH", "MEHHH"),
                    ("BAD", "BAD"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="dailyquestionnaire",
            name="skin_feel",
            field=models.CharField(
                choices=[
                    ("NORMAL", "NORMAL"),
                    ("SENSITIVE", "SENSITIVE"),
                    ("DEHYDRATED", "DEHYDRATED"),
                    ("GREASY", "GREASY"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="eveningquestionnaire",
            name="exercise_hours",
            field=models.CharField(
                choices=[
                    ("TWO_PLUS", "TWO_PLUS"),
                    ("TWO_HOURS", "TWO_HOURS"),
                    ("ONE_AND_A_HALF_HOURS", "ONE_AND_A_HALF_HOURS"),
                    ("ONE_HOUR", "ONE_HOUR"),
                    ("FORTY_FIVE_MIN", "FORTY_FIVE_MIN"),
                    ("THIRTY_MIN", "THIRTY_MIN"),
                    ("TWENTY_MIN", "TWENTY_MIN"),
                    ("ZERO", "ZERO"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="eveningquestionnaire",
            name="skin_feel",
            field=models.CharField(
                choices=[
                    ("NORMAL", "NORMAL"),
                    ("SENSITIVE", "SENSITIVE"),
                    ("DEHYDRATED", "DEHYDRATED"),
                    ("GREASY", "GREASY"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="morningquestionnaire",
            name="feeling_today",
            field=models.CharField(
                choices=[
                    ("LOVE_IT", "LOVE_IT"),
                    ("WELL", "WELL"),
                    ("MEHHH", "MEHHH"),
                    ("BAD", "BAD"),
                ],
                max_length=30,
            ),
        ),
    ]
