import os
import subprocess
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Set or update Heroku config vars from .env file'

    def handle(self, *args, **options):
        app_name = input("Enter the Heroku app name: ")

        # Read variables from .env file
        env_vars = {}
        key = None
        value_lines = []

        with open('.env', 'r') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if '=' in line and key is None:
                    key, value = line.split('=', 1)
                    if value.startswith('\'') and value.endswith('\''):
                        env_vars[key] = value.strip('\'')
                        key = None
                    elif value.startswith('{'):
                        value_lines.append(value)
                    else:
                        env_vars[key] = value
                        key = None
                elif key:
                    value_lines.append(line)
                    if line.endswith('}'):
                        env_vars[key] = '\n'.join(value_lines)
                        key = None
                        value_lines = []

        # Set or update Heroku config vars for variables found in .env file
        for key, value in env_vars.items():
            subprocess.run(['heroku', 'config:set', f'{key}={value}', '--app', app_name])
            self.stdout.write(self.style.SUCCESS(f'Set or updated Heroku config var: {key}'))

        self.stdout.write(self.style.SUCCESS(f'Heroku config vars set or updated successfully for app: {app_name}'))
