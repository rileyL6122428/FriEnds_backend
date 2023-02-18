import json

from channels.generic.websocket import WebsocketConsumer


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        parsed_text_data = json.loads(text_data)
        message = parsed_text_data["message"]
        self.send(
            text_data=json.dumps({"message": f"echo: {message}"}),
        )
