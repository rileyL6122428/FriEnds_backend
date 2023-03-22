import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.db import database_sync_to_async
from .models import Client
from chat import ws_message_handlers


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
        await self.channel_layer.group_add("ALL_USERS", self.channel_name)

    async def disconnect(self, close_code):
        await self.register_client_disconnect()
        await self.channel_layer.group_discard("ALL_USERS", self.channel_name)

    async def forward_broadcast(self, event):
        await self.send(text_data=json.dumps(event["broadcast_message"]))

    async def receive(self, text_data):
        message = json.loads(text_data)["message"]
        client = await self.get_client()

        HandlerClasses = [
            ws_message_handlers.NaiveCreateUserHandler,
            ws_message_handlers.NaiveAuthHandler,
            ws_message_handlers.RoomInfoHandler,
            ws_message_handlers.JoinRoomHandler,
            ws_message_handlers.LeaveRoomHandler,
            ws_message_handlers.AuthedUserHandler,
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

    @database_sync_to_async
    def get_client(self):
        return Client.objects.get(
            channel_name=self.channel_name,
        )

    @database_sync_to_async
    def create_client(self):
        client = Client.objects.create(
            channel_name=self.channel_name,
            connected=True,
        )
        self.client = client

    @database_sync_to_async
    def register_client_disconnect(self):
        client = Client.objects.get(
            channel_name=self.channel_name,
        )
        client.connected = False
        client.save()
