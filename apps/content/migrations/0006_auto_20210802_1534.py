# Generated by Django 3.2.6 on 2021-08-02 15:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0005_auto_20210729_1321"),
    ]

    operations = [
        migrations.AlterField(
            model_name="article",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="articles",
                to="content.category",
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="period",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="articles",
                to="content.period",
            ),
        ),
        migrations.AlterField(
            model_name="category",
            name="name",
            field=models.CharField(
                choices=[
                    ("CORE_PROGRAM", "CORE_PROGRAM"),
                    ("SKIN_STORIES", "SKIN_STORIES"),
                    ("SKIN_SCHOOL", "SKIN_SCHOOL"),
                ],
                max_length=30,
            ),
        ),
    ]
