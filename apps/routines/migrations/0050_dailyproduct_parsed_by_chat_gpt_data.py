# Generated by Django 3.2.15 on 2023-10-31 15:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0049_alter_dailyproduct_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailyproduct",
            name="parsed_by_chat_gpt_data",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
