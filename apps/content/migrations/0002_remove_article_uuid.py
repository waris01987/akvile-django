# Generated by Django 3.2.4 on 2021-07-09 10:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="article",
            name="uuid",
        ),
    ]
