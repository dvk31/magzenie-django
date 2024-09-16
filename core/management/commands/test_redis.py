from django.core.management.base import BaseCommand
from django.conf import settings
from celery import Celery

import logging

class Command(BaseCommand):
    help = 'Test Celery connection to Redis'
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        try:
            self.logger.debug("Creating a Celery app instance.")
            # Create a Celery app instance
            app = Celery('myapp', broker=settings.CELERY_BROKER_URL)

            self.logger.debug("Attempting to connect to Redis.")
            # Ping the Redis server using Celery
            connection = app.connection()
            connection.connect()

            if connection.connected:
                self.stdout.write(self.style.SUCCESS('Celery connection to Redis successful!'))
                self.logger.info("Celery successfully connected to Redis.")
            else:
                self.stdout.write(self.style.ERROR('Celery connection to Redis failed.'))
                self.logger.warning("Failed to connect to Redis.")

            connection.release()
            self.logger.debug("Connection to Redis released.")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error connecting to Redis via Celery: {str(e)}'))
            self.logger.error(f"Exception occurred while connecting to Redis: {str(e)}")