# Generated by Django 3.2.15 on 2023-05-09 20:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0037_auto_20230412_1255"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScrapedProduct",
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
                ("brand", models.CharField(max_length=255)),
                ("title", models.CharField(max_length=255)),
                ("ingredients", models.TextField()),
                ("url", models.URLField()),
                ("job_id", models.CharField(max_length=255)),
                ("status_code", models.IntegerField()),
                ("created_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField()),
            ],
        ),
    ]