# Generated by Django 3.2.11 on 2022-03-21 09:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0006_alter_eveningquestionnaire_exercise_hours"),
    ]

    operations = [
        migrations.AddField(
            model_name="facescan",
            name="haut_ai_batch_id",
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name="facescan",
            name="haut_ai_image_id",
            field=models.CharField(blank=True, max_length=250),
        ),
    ]
