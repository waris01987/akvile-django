# Generated by Django 3.2.12 on 2022-04-20 07:31

import ckeditor.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0015_auto_20220419_0705"),
    ]

    operations = [
        migrations.AddField(
            model_name="articletranslation",
            name="subtitle",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="articletranslation",
            name="headline",
            field=ckeditor.fields.RichTextField(),
        ),
        migrations.AlterField(
            model_name="subcategorytranslation",
            name="description",
            field=models.TextField(blank=True),
        ),
    ]