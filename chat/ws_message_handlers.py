import json
import random
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.auth import login
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Room, Client
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
class RoomInfoHandler(MessageHandler):
    message_types: ClassVar[list[str]] = ["room_info"]

    async def handle(self, message_data):
        if not self.scope["user"].is_authenticated:
            return

        await self.send(
            text_data=json.dumps(
                {
                    "type": "room_info",
                    "rooms": await self.get_room_info(),
                }
            )
        )

    @database_sync_to_async
    def get_room_info(self):
        return [
            {
                "name": room.name,
                "capacity": 2,
                "occupants": [user.username for user in room.occupants.all()],
            }
            for room in Room.objects.all().prefetch_related("occupants")
        ]


@dataclass
class JoinRoomHandler(MessageHandler):
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
            room = await self.add_user_to_room(room)
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "joined_room",
                        "room_name": room.name,
                    }
                )
            )

    @database_sync_to_async
    def already_in_room(self) -> bool:
        user: User = self.scope["user"]
        return user.room_set.exists()

    @database_sync_to_async
    def get_room(self, room_name: str):
        return Room.objects.filter(name=room_name).first()

    @database_sync_to_async
    def add_user_to_room(self, room: Room):
        room.occupants.add(self.scope["user"])
        room.save()
        return room

    @database_sync_to_async
    def is_full(self, room: Room):
        return room.is_full()


@dataclass
class LeaveRoomHandler(MessageHandler):
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
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "left_room",
                        "room_name": room.name,
                    }
                )
            )

    @database_sync_to_async
    def get_room(self):
        user: User = self.scope["user"]
        return Room.objects.filter(occupants__in=[user]).first()

    @database_sync_to_async
    def remove_user_from(self, room: Room):
        user: User = self.scope["user"]
        room.occupants.remove(user)
        room.save()
