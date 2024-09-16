# myapp/management/commands/deploy_to_heroku.py
from django.core.management.base import BaseCommand
import subprocess

class Command(BaseCommand):
    help = "Deploys the app to Heroku using Docker."

    def handle(self, *args, **kwargs):
        app_name = input("Enter the name of the Heroku app you want to create: ")

        # Function to run a command and print its output
        def run_command(command):
            try:
                self.stdout.write(f"Running: {command}")
                result = subprocess.check_output(command, shell=True).decode('utf-8')
                self.stdout.write(result)
            except subprocess.CalledProcessError as e:
                self.stderr.write(e.output.decode('utf-8'))
                self.stderr.write("Error occurred. Exiting.")
                exit(1)

        # 1. Create a new Heroku App
        run_command(f"heroku create {app_name}")

        # 2. Set Heroku to use Containers
        run_command(f"heroku stack:set container -a {app_name}")

        # 3. Log in to Heroku Container Registry
        run_command("heroku container:login")

        # 4. Push the Docker Image to Heroku
        run_command(f"heroku container:push web -a {app_name}")

        # 5. Release the Docker Image on Heroku
        run_command(f"heroku container:release web -a {app_name}")

        self.stdout.write("Deployment to Heroku completed.")