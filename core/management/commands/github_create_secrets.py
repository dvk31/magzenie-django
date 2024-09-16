import os
import requests
import base64
from dotenv import load_dotenv, dotenv_values
from nacl import public, encoding
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Create GitHub secrets from .env file'

    def handle(self, *args, **kwargs):
        load_dotenv()

        # Read environment variables directly from the .env file
        env_vars = dotenv_values()

        # GitHub repository details
        repo_owner = env_vars.get('GITHUB_REPO_OWNER')
        repo_name = env_vars.get('GITHUB_REPO_NAME')
        github_token = env_vars.get('GITHUB_TOKEN')

        if not all([repo_owner, repo_name, github_token]):
            self.stderr.write("GITHUB_REPO_OWNER, GITHUB_REPO_NAME, and GITHUB_TOKEN must be set in the .env file")
            return

        # GitHub API URL
        api_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets'

        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        # Get the public key
        response = requests.get(f'{api_url}/public-key', headers=headers)
        if response.status_code != 200:
            self.stderr.write(f"Error fetching public key: {response.json()}")
            return

        public_key_data = response.json()
        key_id = public_key_data['key_id']
        public_key = public_key_data['key']

        # Encrypt the secrets using the public key
        for env_key, value in env_vars.items():
            if value:
                encrypted_value = self.encrypt_secret(public_key, value)
                self.create_or_update_secret(api_url, env_key, encrypted_value, key_id, headers)

    def encrypt_secret(self, public_key, secret_value):
        """Encrypts a secret using the public key."""
        # Fix base64 padding if necessary
        public_key += '=' * (-len(public_key) % 4)
        
        public_key_bytes = base64.b64decode(public_key)
        public_key_obj = public.PublicKey(public_key_bytes)
        sealed_box = public.SealedBox(public_key_obj)
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        return base64.b64encode(encrypted).decode("utf-8")

    def create_or_update_secret(self, api_url, secret_name, encrypted_value, key_id, headers):
        """Creates or updates a secret in the GitHub repository."""
        data = {
            'encrypted_value': encrypted_value,
            'key_id': key_id
        }

        response = requests.put(f'{api_url}/{secret_name}', headers=headers, json=data)
        if response.status_code == 201:
            self.stdout.write(self.style.SUCCESS(f'Successfully created secret {secret_name}'))
        elif response.status_code == 204:
            self.stdout.write(self.style.SUCCESS(f'Successfully updated secret {secret_name}'))
        else:
            self.stderr.write(f"Error creating/updating secret {secret_name}: {response.json()}")