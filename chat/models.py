from django.db import models
from django.contrib.auth.models import User


class Client(models.Model):
    channel_name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    connection_time = models.DateTimeField(auto_now_add=True)


# Create your models here.
class Room(models.Model):
    name = models.CharField(max_length=255)
    occupants = models.ManyToManyField(User)

    def is_full(self):
        return self.occupants.count() >= 2

    def ready_to_start_game(self):
        return self.is_full()


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    order = models.IntegerField()
    game = models.ForeignKey("Game", on_delete=models.CASCADE)

    def __str__(self):
        return self.user


class GameBoard(models.Model):
    width = models.IntegerField()
    height = models.IntegerField()


class GamePiece(models.Model):
    owner = models.ForeignKey(Player, on_delete=models.CASCADE)
    x_coord = models.IntegerField()
    y_coord = models.IntegerField()
    name = models.CharField(max_length=255)
    board = models.ForeignKey(GameBoard, on_delete=models.CASCADE)

    def __str__(self):
        return self.piece


class Game(models.Model):
    room = models.OneToOneField(Room, on_delete=models.CASCADE)
    turn = models.IntegerField()
    phase = models.IntegerField()
    board = models.ForeignKey(GameBoard, on_delete=models.CASCADE)

    @classmethod
    def create(cls, room: Room):
        board = GameBoard.objects.create(
            width=10,
            height=10,
        )
        board.save()

        new_game = cls(room=room, turn=0, phase=0, board=board)
        new_game.save()

        for index, player in enumerate(room.occupants.all().order_by("id")):
            player = Player.objects.create(
                user=player,
                order=index,
                game=new_game,
            )
            player.save()
            piece = GamePiece.objects.create(
                owner=player,
                x_coord=index,
                y_coord=index,
                name=f"player_{player.id}_piece",
                board=board,
            )
            piece.save()

        return new_game

    def __str__(self):
        return self.board
