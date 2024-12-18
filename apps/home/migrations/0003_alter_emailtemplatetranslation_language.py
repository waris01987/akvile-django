# Generated by Django 3.2.4 on 2021-06-16 14:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("translations", "0003_alter_translation_language"),
        ("home", "0002_auto_20210611_1318"),
    ]

    operations = [
        migrations.AlterField(
            model_name="emailtemplatetranslation",
            name="language",
            field=models.ForeignKey(
                default="en",
                on_delete=django.db.models.deletion.SET_DEFAULT,
                to="translations.language",
            ),
        ),
    ]