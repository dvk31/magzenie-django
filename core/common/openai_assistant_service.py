import requests
import time
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self, assistant_id):
        self.assistant_id = assistant_id
        self.openai_api_key = settings.OPENAI_API_KEY

    def create_thread(self, messages):
        url = 'https://api.openai.com/v1/threads'
        headers = self._get_headers()
        data = {
            'messages': [{'role': 'user', 'content': message} for message in messages]
        }
        logger.debug(f"Creating thread with URL: {url} and data: {data}")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def run_assistant(self, thread_id):
        url = f'https://api.openai.com/v1/threads/{thread_id}/runs'
        headers = self._get_headers()
        data = {
            'assistant_id': self.assistant_id
        }
        logger.debug(f"Running assistant with URL: {url} and data: {data}")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def get_run_status(self, thread_id, run_id):
        url = f'https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}'
        headers = self._get_headers()
        logger.debug(f"Getting run status with URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_response_messages(self, thread_id):
        url = f'https://api.openai.com/v1/threads/{thread_id}/messages'
        headers = self._get_headers()
        logger.debug(f"Getting response messages with URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_data = response.json()

        if 'data' not in response_data:
            logger.error(f"Unexpected response format: {response_data}")
            return {"error": "Unexpected response format"}

        messages = response_data['data']
        return [msg['content'][0]['text']['value'] for msg in messages if msg['role'] == 'assistant']

    def _get_headers(self):
        return {
            'Authorization': f'Bearer {self.openai_api_key}',
            'Content-Type': 'application/json',
            'OpenAI-Beta': 'assistants=v2'
        }