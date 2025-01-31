# Generated by Django 3.2.15 on 2023-11-28 12:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0054_auto_20231127_1616"),
    ]

    operations = [
        migrations.AddField(
            model_name="scrapedproduct",
            name="be_aware",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="scrapedproduct",
            name="good_for",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="scrapedproduct",
            name="recommended_product",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="scrapedproduct",
            name="type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("CLEANSER", "CLEANSER"),
                    ("MOISTURIZER", "MOISTURIZER"),
                    ("TREATMENT", "TREATMENT"),
                ],
                max_length=11,
            ),
        ),
    ]
