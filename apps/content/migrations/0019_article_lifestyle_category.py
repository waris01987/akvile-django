# Generated by Django 3.2.15 on 2022-10-03 08:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0018_auto_20220426_0400"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="lifestyle_category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("NUTRITION", "NUTRITION"),
                    ("SLEEP", "SLEEP"),
                    ("STRESS", "STRESS"),
                    ("EXERCISE", "EXERCISE"),
                ],
                default="",
                max_length=10,
            ),
        ),
    ]
