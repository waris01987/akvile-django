# Generated by Django 3.2.15 on 2023-11-29 14:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0057_rename_good_for_scrapedproduct_positive_effects"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="dailyproduct",
            name="One group per type",
        ),
    ]
