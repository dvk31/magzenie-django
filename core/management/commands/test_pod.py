# core/management/commands/test_pod_request.py
import requests
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Simulates a request from the Universal React Client to test the middleware and pod routing'

    def handle(self, *args, **kwargs):
        # Hardcoded values for testing
        token = 'your_token_here'  # Replace with a valid token
        email = 'user@example.com'
        password = 'securepassword123'

        headers = {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json',
        }

        data = {
            'email': email,
            'password': password,
            'first_name': 'John',
            'last_name': 'Doe'
        }

        url = f"{settings.CORE_API_URL}/api/user/signup/"

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 201:
            self.stdout.write(self.style.SUCCESS(f'Successfully created user: {response.json()}'))
        else:
            self.stdout.write(self.style.ERROR(f'Failed to create user: {response.status_code} - {response.json()}'))