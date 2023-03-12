import json
import random
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.auth import login, get_user
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from .models import Room, Game, Client


class FriEndsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        # if username := self.scope['session']['username']:
        #     user = await self.get_user(username)
        # else:

        # user: User = self.scope["user"]
        # user = await get_user(self.scope)
        # if not user.is_authenticated:
        #     user = await self.create_user()
        #     await login(self.scope, user)
        #     await database_sync_to_async(self.scope["session"].save)()
        # self.scope["session"]["randomkey"] = random.randint(0, 100)

        # await self.channel_layer.group_add(
        #     "UNAUTHENTICATED_USERS",
        #     self.channel_name,
        #     expiry=10,
        # )

        # await self.channel_layer.group_add(
        #     "ALL_USERS",
        #     self.channel_name,
        # )
        await self.create_client()

        await self.accept()

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
        await self.delete_client()
        # await self.channel_layer.group_discard(
        #     "ALL_USERS",
        #     self.channel_name,
        # )

    # Receive message from WebSocket
    async def receive(self, text_data):
        message = json.loads(text_data)["message"]
        match message["type"]:
            case "room_info":
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "room_info",
                            "rooms": await self.get_room_info(),
                        }
                    )
                )

            case "join_room":
                room_name = message["room_name"]
                room, ready_to_start_game = await self.add_user_to_room(
                    room_name=room_name,
                    user=self.scope["user"],
                )

                if room:
                    await self.send(
                        text_data=json.dumps(
                            {
                                "type": "room_joined",
                                "room_name": room_name,
                            }
                        )
                    )
                    await self.channel_layer.group_send(
                        "ALL_USERS",
                        {
                            "type": "group_send",
                            "message": {
                                "type": "room_info",
                                "rooms": await self.get_room_info(),
                            },
                        },
                    )

                    if ready_to_start_game:
                        await self.channel_layer.group_send(
                            room_name,
                            {
                                "type": "chat_message",
                                "message": {
                                    "type": "game_starting",
                                    "message": "game_starting",
                                },
                            },
                        )

                        await self.channel_layer.group_send(
                            room_name,
                            {
                                "type": "chat_message",
                                "message": {
                                    "type": "game_started",
                                    "message": "Game started!",
                                },
                            },
                        )
                else:
                    await self.send(
                        text_data=json.dumps(
                            {
                                "type": "room_full",
                                "room_name": room_name,
                            }
                        )
                    )

        await database_sync_to_async(self.scope["session"].save)()

    @database_sync_to_async
    def create_client(self):
        return Client.objects.create(
            channel_name=self.channel_name,
        )

    @database_sync_to_async
    def delete_client(self):
        Client.objects.filter(
            channel_name=self.channel_name,
        ).delete()

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
