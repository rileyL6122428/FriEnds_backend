# Generated by Django 4.1.7 on 2023-03-23 01:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0014_gamepiece"),
    ]

    operations = [
        migrations.AddField(
            model_name="player",
            name="order",
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
