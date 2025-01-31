# Generated by Django 3.2.4 on 2021-07-29 13:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0004_auto_20210728_0729"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="article",
            options={"ordering": ["ordering"]},
        ),
        migrations.AddField(
            model_name="article",
            name="ordering",
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name="article",
            name="period",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="articles",
                to="content.period",
            ),
        ),
    ]
