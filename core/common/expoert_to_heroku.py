import os
import subprocess
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Exports keys from .env to Heroku"

    def handle(self, *args, **kwargs):
        if not os.path.exists(".env"):
            self.stdout.write(self.style.ERROR("No .env file found."))
            return

        with open(".env", "r") as f:
            lines = f.readlines()

        for line in lines:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                self.set_heroku_var(key, value)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully exported {key} with value {value} to Heroku."
                    )
                )

    def set_heroku_var(self, key, value):
        """Sets a variable on Heroku using the Heroku CLI."""
        command = ["heroku", "config:set", f"{key}={value}"]

        subprocess.run(command)
        print(f"Exported: {key} = {value}")
