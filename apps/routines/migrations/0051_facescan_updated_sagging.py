# Generated by Django 3.2.15 on 2023-11-01 14:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0050_dailyproduct_parsed_by_chat_gpt_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="facescan",
            name="updated_sagging",
            field=models.BooleanField(default=False),
        ),
    ]
