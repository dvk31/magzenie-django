import os
import subprocess
import logging
import docker
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Deploys an app from a given GitHub URL'

    def add_arguments(self, parser):
        parser.add_argument('github_url', type=str, help='The GitHub URL of the application to deploy.')

    def handle(self, *args, **kwargs):
        github_url = kwargs['github_url']
        target_dir = 'devapps'  # relative path

        self.ensure_directory(target_dir)
        self.clone_or_pull_repository(github_url, target_dir)
        self.run_docker_compose(target_dir)
        self.display_container_info()

    def ensure_directory(self, target_dir):
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir)
            except OSError as e:
                error_msg = f"Error creating directory {target_dir}: {str(e)}"
                logger.error(error_msg)
                raise CommandError(error_msg)

    def clone_or_pull_repository(self, github_url, target_dir):
        if os.path.exists(os.path.join(target_dir, ".git")):  # Check if .git folder exists, indicating it's a git repo
            try:
                subprocess.check_call(['git', 'pull', github_url], cwd=target_dir)
            except subprocess.CalledProcessError as e:
                error_msg = f"Failed to pull the latest changes from the GitHub repository: {str(e)}"
                logger.error(error_msg)
                raise CommandError(error_msg)
        else:
            try:
                subprocess.check_call(['git', 'clone', github_url, target_dir])
            except subprocess.CalledProcessError as e:
                error_msg = f"Failed to clone the GitHub repository: {str(e)}"
                logger.error(error_msg)
                raise CommandError(error_msg)

    def run_docker_compose(self, target_dir):
        try:
            process = subprocess.Popen(['docker-compose', 'up', '-d'], stdin=subprocess.PIPE, cwd=target_dir)
            process.communicate(input=b'y\n')
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args)
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to start Docker services: {str(e)}"
            logger.error(error_msg)
            raise CommandError(error_msg)


    def display_container_info(self):
        client = docker.from_env()
        container_info = {}
        for container in client.containers.list():
            container_info[container.name] = {
                'status': container.status,
                'ports': container.attrs['NetworkSettings']['Ports']
            }

        self.stdout.write(self.style.SUCCESS('Deployment successful.'))
        for name, info in container_info.items():
            self.stdout.write(f"Container Name: {name}, Status: {info['status']}, Ports: {info['ports']}")