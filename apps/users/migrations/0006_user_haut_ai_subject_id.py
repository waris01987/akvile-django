# Generated by Django 3.2.11 on 2022-03-21 09:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_remove_user_articles_read"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="haut_ai_subject_id",
            field=models.CharField(blank=True, max_length=250),
        ),
    ]