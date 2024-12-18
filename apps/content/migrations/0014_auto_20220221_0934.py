# Generated by Django 3.2.6 on 2022-02-21 09:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0013_article_article_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="userarticle",
            name="read_at",
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name="category",
            name="name",
            field=models.CharField(
                choices=[
                    ("CORE_PROGRAM", "CORE_PROGRAM"),
                    ("SKIN_STORIES", "SKIN_STORIES"),
                    ("SKIN_SCHOOL", "SKIN_SCHOOL"),
                    ("RECIPES", "RECIPES"),
                    ("INITIAL", "INITIAL"),
                ],
                max_length=30,
            ),
        ),
    ]