# user/apps.py
from django.apps import AppConfig

class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'  # Ensure this matches the name of your app

    def ready(self):
        # Import and connect your signals here
        import user.signals  # Adjust this import path if necessary
