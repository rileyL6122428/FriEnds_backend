from django.db import models
from django.contrib.auth.models import User


class Client(models.Model):
    channel_name = models.CharField(max_length=255)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    connection_time = models.DateTimeField(auto_now_add=True)
    last_authed_message_time = models.DateTimeField(auto_now_add=False, null=True)
    connected = models.BooleanField(default=True)


REQUIRED_PLAYER_COUNT = 2


# Create your models here.
class Room(models.Model):
    name = models.CharField(max_length=255)
    occupants = models.ManyToManyField(User)

    def is_full(self):
        return self.occupants.count() >= REQUIRED_PLAYER_COUNT

    def ready_to_start_game(self):
        return self.is_full()

    def add_occupant(self, user: User):
        self.occupants.add(user)
        self.save()
        Player.objects.create(
            user=user,
            game=self.game,
        )

    def remove_occupant(self, user: User):
        self.occupants.remove(user)
        self.save()
        player = Player.objects.get(user=user)
        player.delete()


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # order = models.IntegerField()
    game = models.ForeignKey("Game", on_delete=models.CASCADE)

    def get_name(self):
        return self.user.username

    def __str__(self):
        return self.user


# class GameBoard(models.Model):
#     width = models.IntegerField()
#     height = models.IntegerField()


# class GamePiece(models.Model):
#     owner = models.ForeignKey(Player, on_delete=models.CASCADE)
#     x_coord = models.IntegerField()
#     y_coord = models.IntegerField()
#     name = models.CharField(max_length=255)
#     board = models.ForeignKey(GameBoard, on_delete=models.CASCADE)

#     def __str__(self):
#         return self.piece


class Game(models.Model):
    room = models.OneToOneField(Room, on_delete=models.CASCADE)
    state = models.CharField(
        max_length=255,
        choices=[
            ("waiting", "waiting"),
            ("playing", "playing"),
            ("finished", "finished"),
        ],
        default="waiting",
    )
    # turn = models.IntegerField()
    # phase = models.IntegerField()
    # board = models.ForeignKey(GameBoard, on_delete=models.CASCADE)

    @classmethod
    def create(cls, room: Room):
        new_game = cls(room=room, state="waiting")
        new_game.save()

        for index, player in enumerate(room.occupants.all().order_by("id")):
            player = Player.objects.create(
                user=player,
                order=index,
                game=new_game,
            )
            player.save()

        return new_game

    def __str__(self):
        return self.board
