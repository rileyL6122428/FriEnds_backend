import json
import random
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.auth import login, get_user
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from .models import Room, Game, Client
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
        # DEBUG THIS NEXT
        username = message_data["username"]
        client_name = message_data["client_name"]

        user = await self.get_user(username, client_name)
        if not user:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "authenticate error",
                        "message": "User not found",
                    }
                )
            )

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
        return (
            User.objects.filter(
                username=username,
                client__channel_name=client_name,
            )
            .prefetch_related("client")
            .first()
        )

    @database_sync_to_async
    def assign_client(self, user: User):
        self.client.user = user
        self.client.auth_time = timezone.now()
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


class FriEndsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.create_client()
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "message": (
                        "Connection established! "
                        "Authenticate within the next minute "
                        "or your connection will be closed."
                    ),
                    "client_name": self.client.channel_name,
                    "type": "client_created",
                }
            )
        )

        # await self.send(
        #     text_data=json.dumps(
        #         {
        #             "message": "User created!",
        #             "username": self.username,
        #             "type": "user_created",
        #         }
        #     )
        # )

        # self.scope['session']['username'] = self.username
        # await sync_to_async(self.scope["session"].save)()

    async def disconnect(self, close_code):
        # await self.delete_user()
        await self.register_client_disconnect()
        # await self.channel_layer.group_discard(
        #     "ALL_USERS",
        #     self.channel_name,
        # )

    # Receive message from WebSocket
    async def receive(self, text_data):
        message = json.loads(text_data)["message"]
        client = await self.get_client()

        # NOW IT'S TIME TO TEST THIS OUT
        HandlerClasses = [
            NaiveCreateUserHandler,
            NaiveAuthHandler,
            RoomInfoHandler,
            AuthedUserHandler,
        ]

        for HandlerClass in HandlerClasses:
            if (
                HandlerClass.message_types == ["all"]
                or message["type"] in HandlerClass.message_types
            ):
                handler = HandlerClass(
                    client=client,
                    consumer=self,
                    scope=self.scope,
                )
                await handler.handle(message)

        # message = json.loads(text_data)["message"]
        # match message["type"]:
        #     case "room_info":
        #         await self.send(
        #             text_data=json.dumps(
        #                 {
        #                     "type": "room_info",
        #                     "rooms": await self.get_room_info(),
        #                 }
        #             )
        #         )

        #     case "join_room":
        #         room_name = message["room_name"]
        #         room, ready_to_start_game = await self.add_user_to_room(
        #             room_name=room_name,
        #             user=self.scope["user"],
        #         )

        #         if room:
        #             await self.send(
        #                 text_data=json.dumps(
        #                     {
        #                         "type": "room_joined",
        #                         "room_name": room_name,
        #                     }
        #                 )
        #             )
        #             await self.channel_layer.group_send(
        #                 "ALL_USERS",
        #                 {
        #                     "type": "group_send",
        #                     "message": {
        #                         "type": "room_info",
        #                         "rooms": await self.get_room_info(),
        #                     },
        #                 },
        #             )

        #             if ready_to_start_game:
        #                 await self.channel_layer.group_send(
        #                     room_name,
        #                     {
        #                         "type": "chat_message",
        #                         "message": {
        #                             "type": "game_starting",
        #                             "message": "game_starting",
        #                         },
        #                     },
        #                 )

        #                 await self.channel_layer.group_send(
        #                     room_name,
        #                     {
        #                         "type": "chat_message",
        #                         "message": {
        #                             "type": "game_started",
        #                             "message": "Game started!",
        #                         },
        #                     },
        #                 )
        #         else:
        #             await self.send(
        #                 text_data=json.dumps(
        #                     {
        #                         "type": "room_full",
        #                         "room_name": room_name,
        #                     }
        #                 )
        #             )

        # await database_sync_to_async(self.scope["session"].save)()

    @database_sync_to_async
    def get_client(self):
        return Client.objects.get(
            channel_name=self.channel_name,
        )

    @database_sync_to_async
    def create_client(self):
        client = Client.objects.create(
            channel_name=self.channel_name,
        )
        self.client = client

    @database_sync_to_async
    def register_client_disconnect(self):
        client = Client.objects.get(
            channel_name=self.channel_name,
        )
        client.disconnected = True
        client.save()

    async def group_send(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))

    async def add_user_to_room(self, room_name: str, user: User) -> tuple[Room, bool]:
        room, room_full = await self.add_user_to_room_model(
            room_name=room_name,
            user=user,
        )
        if room:
            await self.channel_layer.group_add(
                room_name,
                self.channel_name,
            )

        return room, room_full

    @database_sync_to_async
    def add_user_to_room_model(self, room_name: str, user: User):
        room, _created = Room.objects.get_or_create(
            name=room_name,
        )
        if not room.is_full():
            room.occupants.add(user)
            room.save()
            return room, room.is_full()

        return None, False

    @database_sync_to_async
    def start_game(self, room: Room):
        game = Game.create(room=room)
        game.save()
        return game

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

    @database_sync_to_async
    def create_user(self):
        user = User.objects.create(
            username=f"Sigurd{random.randint(0, 9999)}",
        )
        self.username = user.username
        return user

    @database_sync_to_async
    def delete_user(self):
        user: User = self.scope["user"]
        user.room_set.clear()
        user.save()
        if user:
            user.delete()
