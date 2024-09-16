from django.core.management.base import BaseCommand
from django.apps import apps
import os

class Command(BaseCommand):
    help = 'Deletes all migration files in all apps except for __init__.py'

    def handle(self, *args, **options):
        app_configs = apps.get_app_configs()
        for app_config in app_configs:
            migrations_dir = os.path.join(app_config.path, 'migrations')
            if os.path.exists(migrations_dir):
                for filename in os.listdir(migrations_dir):
                    if filename != '__init__.py' and filename.endswith('.py'):
                        file_path = os.path.join(migrations_dir, filename)
                        os.remove(file_path)
                        self.stdout.write(self.style.SUCCESS(f'Deleted {file_path}'))
                    elif filename.endswith('.pyc'):
                        file_path = os.path.join(migrations_dir, filename)
                        os.remove(file_path)
                        self.stdout.write(self.style.SUCCESS(f'Deleted {file_path}'))
        self.stdout.write(self.style.SUCCESS('All migration files deleted except __init__.py'))