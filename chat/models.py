import random
from django.db import models
from django.contrib.auth.models import User


class Client(models.Model):
    channel_name = models.CharField(max_length=255)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    connection_time = models.DateTimeField(auto_now_add=True)
    last_authed_message_time = models.DateTimeField(auto_now_add=False, null=True)
    connected = models.BooleanField(default=True)


REQUIRED_PLAYER_COUNT = 2


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
        player = Player.objects.create(
            user=user,
            name=user.username,
            game=self.game,
            order=self.occupants.count() - 1,
        )
        GamePiece.create_at_random_location(player, player.name)
        if self.ready_to_start_game():
            self.game.state = "playing"
            self.game.save()

    def remove_occupant(self, user: User):
        self.occupants.remove(user)
        self.save()
        player = Player.objects.get(user=user)
        player.delete()


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=255)
    order = models.IntegerField()
    game = models.ForeignKey("Game", on_delete=models.CASCADE)

    def get_name(self):
        return self.name


class GameBoard(models.Model):
    rows = models.IntegerField()
    cols = models.IntegerField()

    def get_random_unoccupied_location(self) -> tuple[int, int]:
        all_spaces = set()
        for row in range(self.rows):
            for col in range(self.cols):
                all_spaces.add((col, row))

        occupied_spaces = set()
        for piece in self.gamepiece_set.all():
            occupied_spaces.add((piece.col, piece.row))

        unoccupied_spaces = all_spaces - occupied_spaces
        return random.choice(list(unoccupied_spaces))


class GamePiece(models.Model):
    owner = models.ForeignKey(Player, on_delete=models.CASCADE)
    col = models.IntegerField()
    row = models.IntegerField()
    name = models.CharField(max_length=255)
    board = models.ForeignKey(GameBoard, on_delete=models.CASCADE)

    @classmethod
    def create_at_random_location(cls, owner: Player, name: str):
        board: GameBoard = owner.game.board
        col, row = board.get_random_unoccupied_location()
        return cls.create_at_location(owner, name, col, row)

    @classmethod
    def create_at_location(cls, owner: Player, name: str, col: int, row: int):
        return cls.objects.create(
            owner=owner,
            col=col,
            row=row,
            name=name,
            board=owner.game.board,
        )


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
    board = models.ForeignKey(GameBoard, on_delete=models.CASCADE)

    @classmethod
    def create(cls, room: Room):
        board: GameBoard = GameBoard.objects.create(
            rows=10,
            cols=10,
        )
        new_game = cls(
            room=room,
            state="waiting",
            board=board,
        )
        new_game.save()

        for user in room.occupants.all().order_by("id"):
            player = Player.objects.create(
                user=user,
                name=user.username,
                game=new_game,
            )
            player.save()
            GamePiece.create_at_random_location(
                owner=player,
                name=player.name,
            )

        enemy_player = Player.objects.create(
            name="ENEMY",
            game=new_game,
            order=REQUIRED_PLAYER_COUNT,
        )
        enemy_player.save()
        GamePiece.create_at_random_location(
            owner=enemy_player,
            name=enemy_player.name,
        )

        return new_game
