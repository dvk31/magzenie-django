import json
from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import traceback

class UserConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print(f"Attempting to connect... (Client IP: {self.scope['client'][0]})")
        try:
            await self.accept()
            print(f"WebSocket connected (Client IP: {self.scope['client'][0]})")
            
            # Add a longer delay before sending the initial message
            await asyncio.sleep(2)
            
            await self.send(text_data=json.dumps({
                'message': 'Connected to User service'
            }))
            print(f"Sent initial message (Client IP: {self.scope['client'][0]})")
        except Exception as e:
            print(f"Error in connect: {str(e)} (Client IP: {self.scope['client'][0]})")
            print(traceback.format_exc())

    async def disconnect(self, close_code):
        print(f"WebSocket disconnected with code: {close_code} (Client IP: {self.scope['client'][0]})")

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get('message', '')
            print(f"Received message: {message} (Client IP: {self.scope['client'][0]})")
            response = f"User service received: {message}"
            await self.send(text_data=json.dumps({
                'message': response
            }))
            print(f"Message sent: {response} (Client IP: {self.scope['client'][0]})")
        except Exception as e:
            print(f"Error in receive: {str(e)} (Client IP: {self.scope['client'][0]})")
            print(traceback.format_exc())

    async def send(self, text_data=None, bytes_data=None, close=False):
        try:
            await super().send(text_data, bytes_data, close)
        except Exception as e:
            print(f"Error in send: {str(e)} (Client IP: {self.scope['client'][0]})")
            print(traceback.format_exc())