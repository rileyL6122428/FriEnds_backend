import json
import random
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.auth import login
from django.contrib.auth.models import User
from .models import Room


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = self.room_name

        user = await self.create_user()
        await login(self.scope, user)

        await self.add_user_to_room(
            room_name=self.room_name,
            user=user,
        )

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.delete_user()

        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat_message", "message": message}
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))

    @database_sync_to_async
    def add_user_to_room(self, room_name: str, user: User):
        room, _created = Room.objects.get_or_create(
            name=room_name,
        )
        room.occupants.add(user)
        room.save()
        return room

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
