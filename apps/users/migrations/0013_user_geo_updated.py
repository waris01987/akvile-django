# Generated by Django 3.2.15 on 2023-08-25 10:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0012_alter_user_chat_gpt_history"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="geo_updated",
            field=models.BooleanField(default=False),
        ),
    ]