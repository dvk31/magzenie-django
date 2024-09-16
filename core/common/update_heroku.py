import subprocess
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Updates the deployed Django project on Heroku."

    def add_arguments(self, parser):
        parser.add_argument(
            "app_name", type=str, help="The name of the Heroku app to update."
        )

    def handle(self, *args, **kwargs):
        app_name = kwargs["app_name"]

        # 1. Commit changes to local git repository
        self.commit_changes()

        # 2. Push changes to Heroku
        self.push_to_heroku(app_name)

        # 3. Set DJANGO_SETTINGS_MODULE environment variable on Heroku
        self.set_heroku_settings_module(app_name)

        # 4. Run migrations on Heroku
        self.run_migrations(app_name)

    def commit_changes(self):
        """Commit any changes to the local git repository."""
        commands = [
            ["git", "add", "."],
            ["git", "commit", "-m", "Update for Heroku deployment."],
        ]

        for command in commands:
            subprocess.run(command)
            print(f"Executed: {' '.join(command)}")

    def push_to_heroku(self, app_name):
        """Push changes to Heroku app."""
        command = ["git", "push", f"heroku", "main"]
        subprocess.run(command)
        print(f"Pushed changes to Heroku app: {app_name}")

    def set_heroku_settings_module(self, app_name):
        """Set the DJANGO_SETTINGS_MODULE environment variable on Heroku."""
        command = [
            "heroku",
            "config:set",
            "DJANGO_SETTINGS_MODULE=hellogpt.settings.dev",
            "--app",
            app_name,
        ]
        subprocess.run(command)
        print(f"Set DJANGO_SETTINGS_MODULE for Heroku app: {app_name}")

    def run_migrations(self, app_name):
        """Run migrations on the Heroku app."""
        command = ["heroku", "run", "python manage.py migrate", "--app", app_name]
        subprocess.run(command)
        print(f"Ran migrations on Heroku app: {app_name}")
