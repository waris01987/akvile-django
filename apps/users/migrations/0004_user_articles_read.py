# Generated by Django 3.2.4 on 2021-07-13 10:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0002_remove_article_uuid"),
        ("users", "0003_user_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="articles_read",
            field=models.ManyToManyField(
                blank=True, related_name="read_by_user", to="content.Article"
            ),
        ),
    ]