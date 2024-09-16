import os
import json
import subprocess
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Exports the Google Cloud credentials from a JSON file to a Heroku environment variable'

    def handle(self, *args, **options):
        # Ask for the Heroku app name
        app_name = input("Enter the Heroku app name: ")

        # Define the path to your JSON file
        credentials_path = 'tryoutbotmain-3f44d9722883.json'

        # Check if the file exists
        if not os.path.exists(credentials_path):
            self.stdout.write(self.style.ERROR('Credentials file not found.'))
            return

        # Read the JSON file
        with open(credentials_path, 'r') as file:
            credentials = json.load(file)

        # Convert the dictionary to a JSON string suitable for environment variable
        credentials_json = json.dumps(credentials)

        # Build the Heroku command
        heroku_command = [
            'heroku', 'config:set',
            f'GOOGLE_CREDENTIALS_JSON=\'{credentials_json}\'',
            '--app', app_name
        ]

        # Execute the Heroku command
        try:
            subprocess.run(heroku_command, check=True)
            self.stdout.write(self.style.SUCCESS(f'Successfully set GOOGLE_CREDENTIALS_JSON for {app_name}'))
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR('Failed to set config var on Heroku'))
            self.stdout.write(str(e))