# Generated by Django 3.2.15 on 2023-10-11 15:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0048_auto_20231011_1316"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dailyproduct",
            name="name",
            field=models.TextField(blank=True),
        ),
    ]
