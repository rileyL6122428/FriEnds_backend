# Generated by Django 4.1.7 on 2023-03-11 02:55

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0004_remove_room_occupants_room_occupants"),
    ]

    operations = [
        migrations.CreateModel(
            name="Game",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("turn", models.IntegerField()),
                ("phase", models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name="GameBoard",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("width", models.IntegerField()),
                ("height", models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name="Player",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("order", models.IntegerField()),
                (
                    "game",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="chat.game"
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="GamePiece",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("x_coord", models.IntegerField()),
                ("y_coord", models.IntegerField()),
                ("name", models.CharField(max_length=255)),
                (
                    "board",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="chat.gameboard"
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="chat.player"
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="game",
            name="board",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="chat.gameboard"
            ),
        ),
        migrations.AddField(
            model_name="game",
            name="room",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE, to="chat.room"
            ),
        ),
    ]
