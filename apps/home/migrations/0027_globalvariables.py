# Generated by Django 3.2.15 on 2023-07-24 13:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0026_review"),
    ]

    operations = [
        migrations.CreateModel(
            name="GlobalVariables",
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
                ("indian_paywall", models.BooleanField(default=False)),
            ],
        ),
    ]