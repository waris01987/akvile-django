# Generated by Django 3.2.15 on 2023-11-28 14:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0055_auto_20231128_1229"),
    ]

    operations = [
        migrations.RenameField(
            model_name="scrapedproduct",
            old_name="be_aware",
            new_name="side_effects",
        ),
    ]
