# Generated by Django 3.2.15 on 2023-02-27 11:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0033_auto_20230223_1111"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="dailyproductgroup",
            name="email",
        ),
    ]
