import os
import requests
from dotenv import load_dotenv
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Delete all GitHub secrets in the repository'

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
            self.stderr.write(f"Error fetching secrets: {response.json()}")
            return

        secrets = response.json().get('secrets', [])

        # Delete the secrets
        for secret in secrets:
            secret_name = secret['name']
            delete_response = requests.delete(f'{api_url}/{secret_name}', headers=headers)
            if delete_response.status_code == 204:
                self.stdout.write(self.style.SUCCESS(f'Successfully deleted secret {secret_name}'))
            else:
                self.stderr.write(f"Error deleting secret {secret_name}: {delete_response.json()}")