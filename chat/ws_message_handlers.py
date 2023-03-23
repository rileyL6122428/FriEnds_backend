import json
import random
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.auth import login
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Room, Client, Game, REQUIRED_PLAYER_COUNT
from dataclasses import dataclass
from django.utils import timezone
from typing import ClassVar


@dataclass
class MessageHandler:
    client: Client
    scope: dict
    consumer: AsyncWebsocketConsumer
    message_types: ClassVar[list[str]]

    async def handle(self, message_data):
        raise NotImplementedError()

    async def send(self, text_data):
        return await self.consumer.send(text_data=text_data)


@dataclass
class RoomInfoMixin(MessageHandler):
    @database_sync_to_async
    def get_room_info_message(self):
        return {
            "type": "room_info",
            "rooms": [
                {
                    "name": room.name,
                    "capacity": 2,
                    "occupants": [user.username for user in room.occupants.all()],
                }
                for room in Room.objects.all().prefetch_related("occupants")
            ],
        }

    @database_sync_to_async
    def get_room(self, room_name=None):
        user: User = self.scope["user"]
        if room_name is None:
            room_filter = Room.objects.filter(occupants__in=[user])
        else:
            room_filter = Room.objects.filter(name=room_name)

        return room_filter.prefetch_related(
            "game",
            "game__player_set",
            "game__player_set__user",
            "game__board",
            "game__board__gamepiece_set",
            "game__board__gamepiece_set__owner",
            "occupants",
        ).first()

    async def send_room_not_found(self):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "room error",
                    "error": "Room not found",
                }
            )
        )

    async def send_user_not_in_room(self):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "room error",
                    "error": "User not in room",
                }
            )
        )

    async def send_game_info(self, room: Room):
        await self.send(
            text_data=json.dumps(
                self.get_game_info_message(room.game),
            )
        )

    async def broadcast_game_info(self, room: Room):
        await self.consumer.channel_layer.group_send(
            room.name,
            {
                "type": "forward_broadcast",
                "broadcast_message": self.get_game_info_message(room.game),
            },
        )

    def get_game_info_message(self, game: Game):
        return {
            "type": "game_info",
            "game": {
                "state": game.state,
                "players": [
                    {
                        "name": player.get_name(),
                    }
                    for player in sorted(
                        list(game.player_set.all()),
                        key=lambda player: player.order,
                    )
                ],
                "requiredPlayers": REQUIRED_PLAYER_COUNT,
                "grid": {
                    "cols": game.board.cols,
                    "rows": game.board.rows,
                },
                "boardPieces": [
                    {
                        "name": piece.name,
                        "row": piece.row,
                        "col": piece.col,
                        "player": {"name": piece.owner.name},
                    }
                    for piece in game.board.gamepiece_set.all()
                ],
            },
        }


@dataclass
class NaiveAuthHandler(MessageHandler):
    message_types: ClassVar[list[str]] = ["authenticate"]

    async def handle(self, message_data):
        username = message_data["username"]
        client_name = message_data["client_name"]

        user = await self.get_user(username, client_name)
        if not user:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "authenticate error",
                        "error": "User not found",
                    }
                )
            )
        else:
            user = await self.delete_current_client(user)
            user = await self.assign_client(user)
            await login(self.scope, user)
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "authenticated",
                        "username": user.username,
                        "client_name": user.client.channel_name,
                    }
                )
            )

    @database_sync_to_async
    def get_user(self, username: str, client_name: str):
        user = (
            User.objects.filter(
                username=username,
                client__channel_name=client_name,
            )
            .prefetch_related("client")
            .first()
        )
        return user

    @database_sync_to_async
    def delete_current_client(self, user: User):
        user.client.delete()
        return user

    @database_sync_to_async
    def assign_client(self, user: User):
        self.client.user = user
        self.client.last_authed_message_time = timezone.now()
        self.client.save()
        return user


@dataclass
class NaiveCreateUserHandler(MessageHandler):
    message_types: ClassVar[list[str]] = ["create_user"]

    async def handle(self, message_data):
        user = await self.create_user()
        user = await self.assign_client(user)

        await login(self.scope, user)

        await self.send(
            text_data=json.dumps(
                {
                    "type": "authenticated",
                    "username": user.username,
                    "client_name": user.client.channel_name,
                }
            )
        )

    @database_sync_to_async
    def get_user(self, username: str):
        return User.objects.filter(
            username=username,
        ).first()

    @database_sync_to_async
    def create_user(self):
        fe_char_names = [
            "Sigurd",
            "Erika",
            "Ephraim",
            "Lyn",
            "Hector",
            "Roy",
            "Marth",
            "Alm",
            "Celica",
            "Tiki",
            "Ike",
            "Micaiah",
            "Lucina",
            "Robin",
            "Corrin",
            "Azura",
            "Fjorm",
        ]
        random_fe_char_name = random.choice(fe_char_names)
        user = User.objects.create(
            username=f"{random_fe_char_name}{random.randint(0, 9999)}",
        )
        return user

    @database_sync_to_async
    def assign_client(self, user: User):
        self.client.user = user
        self.client.auth_time = timezone.now()
        self.client.save()
        return user


@dataclass
class AuthedUserHandler(MessageHandler):
    message_types: ClassVar[list[str]] = ["all"]

    async def handle(self, message_data):
        if self.scope["user"].is_authenticated:
            await self.register_authed_message()

    @database_sync_to_async
    def register_authed_message(self):
        self.client.last_authed_message_time = timezone.now()
        self.client.save()


@dataclass
class RoomInfoHandler(RoomInfoMixin):
    message_types: ClassVar[list[str]] = ["room_info"]

    async def handle(self, message_data):
        if not self.scope["user"].is_authenticated:
            return

        await self.send(text_data=json.dumps(await self.get_room_info_message()))


@dataclass
class GameInfoHandler(RoomInfoMixin):
    message_types: ClassVar[list[str]] = ["game_info"]

    async def handle(self, message_data):
        user: User = self.scope["user"]
        if not user.is_authenticated:
            return

        room_name = message_data["room_name"]
        room: Room = await self.get_room(room_name)
        if not room:
            await self.send_room_not_found()
        elif not user in room.occupants.all():
            await self.send_user_not_in_room()
        else:
            await self.send_game_info(room)


@dataclass
class JoinRoomHandler(RoomInfoMixin):
    message_types: ClassVar[list[str]] = ["join_room"]

    async def handle(self, message_data):
        user: User = self.scope["user"]
        if not user.is_authenticated:
            return

        if await self.already_in_room():
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "room error",
                        "error": "User is already in a room",
                    }
                )
            )
            return

        room_name = message_data["room_name"]
        room: Room = await self.get_room(room_name)

        if not room:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "room error",
                        "error": "Room not found",
                    }
                )
            )
        elif await self.is_full(room):
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "room error",
                        "error": "Room is full",
                    }
                )
            )
        else:
            await self.add_user_to_room(room)
            # REFETCH ROOM TO GET UPDATED COPY OF NESTED RELATIONSHIPS
            room = await self.get_room(room_name)

            await self.consumer.channel_layer.group_add(
                room.name,
                self.consumer.channel_name,
            )
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "joined_room",
                        "room_name": room.name,
                    }
                )
            )

            await self.consumer.channel_layer.group_send(
                "ALL_USERS",
                {
                    "type": "forward_broadcast",
                    "broadcast_message": await self.get_room_info_message(),
                },
            )
            await self.broadcast_game_info(room)

    @database_sync_to_async
    def already_in_room(self) -> bool:
        user: User = self.scope["user"]
        return user.room_set.exists()

    @database_sync_to_async
    def add_user_to_room(self, room: Room):
        user: User = self.scope["user"]
        room.add_occupant(user)

    @database_sync_to_async
    def is_full(self, room: Room):
        return room.is_full()


@dataclass
class LeaveRoomHandler(RoomInfoMixin):
    message_types: ClassVar[list[str]] = ["leave_room"]

    async def handle(self, message_data):
        user: User = self.scope["user"]
        if not user.is_authenticated:
            return

        room: Room = await self.get_room()

        if not room:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "leave room error",
                        "error": "Room not found",
                    }
                )
            )
        else:
            await self.remove_user_from(room)
            await self.consumer.channel_layer.group_discard(
                room.name,
                self.consumer.channel_name,
            )
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "left_room",
                        "room_name": room.name,
                    }
                )
            )
            await self.consumer.channel_layer.group_send(
                "ALL_USERS",
                {
                    "type": "forward_broadcast",
                    "broadcast_message": await self.get_room_info_message(),
                },
            )
            await self.broadcast_game_info(room)

    @database_sync_to_async
    def remove_user_from(self, room: Room):
        user: User = self.scope["user"]
        room.remove_occupant(user)
