import os
import base64
import requests
from nacl import encoding, public, secret, utils
from django.core.management.base import BaseCommand
from dotenv import set_key, load_dotenv

class Command(BaseCommand):
    help = 'Download GitHub secrets and apply to the current environment'

    def handle(self, *args, **kwargs):
        load_dotenv()

        # GitHub repository details
        repo_owner = os.getenv('GITHUB_REPO_OWNER')
        repo_name = os.getenv('GITHUB_REPO_NAME')
        github_token = os.getenv('GITHUB_TOKEN')

        if not all([repo_owner, repo_name, github_token]):
            self.stderr.write("GITHUB_REPO_OWNER, GITHUB_REPO_NAME, and GITHUB_TOKEN must be set in the .env file")
            return

        # GitHub API URL
        api_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets'

        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        # Get the list of secrets
        response = requests.get(api_url, headers=headers)
        if response.status_code != 200:
            self.stderr.write(f"Error fetching secrets list: {response.json()}")
            return

        secrets = response.json().get('secrets', [])

        for secret in secrets:
            secret_name = secret['name']
            self.download_and_apply_secret(api_url, secret_name, headers)

    def download_and_apply_secret(self, api_url, secret_name, headers):
        """Download a secret from GitHub and apply it to the environment."""
        secret_url = f'{api_url}/{secret_name}'
        response = requests.get(secret_url, headers=headers)
        if response.status_code != 200:
            self.stderr.write(f"Error fetching secret {secret_name}: {response.json()}")
            return

        secret_data = response.json()
        encrypted_value = secret_data['encrypted_value']
        key_id = secret_data['key_id']

        # Decrypt the secret value using the key_id (assuming you have a way to get the private key)
        # For this example, we'll assume the private key is available in the environment
        private_key = os.getenv('PRIVATE_KEY')
        if not private_key:
            self.stderr.write(f"PRIVATE_KEY must be set in the .env file to decrypt secrets.")
            return

        decrypted_value = self.decrypt_secret(private_key, encrypted_value)
        if decrypted_value:
            # Apply the secret to the environment
            env_path = os.path.join(os.path.dirname(__file__), '../../../.env')
            set_key(env_path, secret_name, decrypted_value)
            self.stdout.write(self.style.SUCCESS(f'Successfully applied secret {secret_name}'))

    def decrypt_secret(self, private_key, encrypted_value):
        """Decrypts a secret using the private key."""
        try:
            private_key_bytes = base64.b64decode(private_key)
            encrypted_bytes = base64.b64decode(encrypted_value)
            private_key_obj = public.PrivateKey(private_key_bytes)
            sealed_box = public.SealedBox(private_key_obj)
            decrypted = sealed_box.decrypt(encrypted_bytes)
            return decrypted.decode("utf-8")
        except Exception as e:
            self.stderr.write(f"Error decrypting secret: {e}")
            return None