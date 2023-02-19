import json
import random
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.auth import login
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Room


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = self.room_name

        user = await self.create_user()
        await login(self.scope, user)

        # await self.add_user_to_room(
        #     room_name=self.room_name,
        #     user=user,
        # )

        # # Join room group
        await self.channel_layer.group_add(
            "ALL_USERS",
            self.channel_name,
        )

        await self.accept()

        await self.send(
            text_data=json.dumps(
                {
                    "message": "User created!",
                    "username": self.username,
                    "type": "user_created",
                }
            )
        )

    async def disconnect(self, close_code):
        await self.delete_user()

        await self.channel_layer.group_discard(
            "ALL_USERS",
            self.channel_name,
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        message = json.loads(text_data)["message"]
        # if message["type"] == "room_info":
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
                room = await self.add_user_to_room(
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
                else:
                    await self.send(
                        text_data=json.dumps(
                            {
                                "type": "room_full",
                                "room_name": room_name,
                            }
                        )
                    )

        # message = text_data_json["message"]

        # Send message to room group
        # await self.channel_layer.group_send(
        #     self.room_group_name,
        #     {"type": "chat_message", "message": message},
        # )

    async def group_send(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))

    async def add_user_to_room(self, room_name: str, user: User):
        room = await self.add_user_to_room_model(
            room_name=room_name,
            user=user,
        )
        if room:
            await self.channel_layer.group_add(
                room_name,
                self.channel_name,
            )
        return room

    @database_sync_to_async
    def add_user_to_room_model(self, room_name: str, user: User):
        room, _created = Room.objects.get_or_create(
            name=room_name,
        )
        if not room.is_full():
            room.occupants.add(user)
            room.save()
            return room

        return None

    @database_sync_to_async
    def get_room_info(self):
        return [
            {
                "name": room.name,
                "capacity": f"{room.occupants.count()}/2",
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
        if user:
            user.delete()
