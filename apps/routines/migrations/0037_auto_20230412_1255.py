# Generated by Django 3.2.15 on 2023-04-12 12:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0036_dailyproducttemplate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dailyproduct",
            name="ingredients",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="dailyproducttemplate",
            name="ingredients",
            field=models.TextField(),
        ),
    ]
