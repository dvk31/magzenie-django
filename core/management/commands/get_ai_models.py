import os
import logging
import requests
from django.core.management.base import BaseCommand
from webhook.models import AIModelProvider, AIModel

logger = logging.getLogger(__name__)
openai_api_key = os.getenv('OPENAI_API_KEY')


class Command(BaseCommand):
    help = 'Fetches AI models from providers and logs the response'

    def handle(self, *args, **kwargs):
        try:
            headers = {
                'Authorization': f'Bearer {openai_api_key}',
                'Content-Type': 'application/json'
            }
            response = requests.get('https://api.openai.com/v1/models', headers=headers)
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
            models = response.json()['data']
            logger.info(f"Response from OpenAI: {models}")

            # Create or update AIModelProvider and AIModel instances
            provider, _ = AIModelProvider.objects.get_or_create(name='OpenAI')
            for model_data in models:
                model_name = model_data['id']
                AIModel.objects.update_or_create(
                    provider=provider,
                    model_name=model_name
                )

            self.stdout.write(self.style.SUCCESS('Logged response from OpenAI and updated models'))
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred while fetching models from OpenAI: {str(e)}", exc_info=True)
            self.stdout.write(self.style.ERROR('Failed to fetch models from OpenAI'))