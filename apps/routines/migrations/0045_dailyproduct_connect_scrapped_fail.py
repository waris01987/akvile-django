# Generated by Django 3.2.15 on 2023-08-29 08:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0044_dailyproduct_image_parse_fail"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailyproduct",
            name="connect_scrapped_fail",
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]