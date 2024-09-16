from django.core.management.base import BaseCommand
from user.models import DefaultEnvironmentVariable

class Command(BaseCommand):
    help = 'Populate DefaultEnvironmentVariable with default values from .env file'

    def handle(self, *args, **kwargs):
        default_env_vars = {
            'SECRET_KEY': 'django-insecure-2ctjl=dh!bb)v2p-#ili=0wf((71drma9-+&jd31#05=8&eeil',
            'DEBUG': 'True',
            'DATABASE_ENGINE': 'django.db.backends.sqlite3',
            'DATABASE_NAME': 'db.sqlite3',
            'SECURE_SSL_REDIRECT': 'False',
            'SESSION_COOKIE_SECURE': 'False',
            'CSRF_COOKIE_SECURE': 'False',
            'SECURE_HSTS_SECONDS': '0',
            'SECURE_HSTS_INCLUDE_SUBDOMAINS': 'False',
            'SECURE_HSTS_PRELOAD': 'False',
        }

        for key, value in default_env_vars.items():
            DefaultEnvironmentVariable.objects.update_or_create(key=key, defaults={'value': value})
        
        self.stdout.write(self.style.SUCCESS('Successfully populated default environment variables.'))