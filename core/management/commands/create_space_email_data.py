import logging
import traceback
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from space.models import Space
from emails.models import EmailData
from space.models import SpaceFeedData, SpaceFeed
from space.signals.create_space_email_data_for_existing import create_space_email_data_task_for_existing

logger = logging.getLogger(__name__)



class Command(BaseCommand):
    help = 'Ensure all existing Spaces have corresponding EmailData, SpaceFeedData, and SpaceFeed instances'

    def handle(self, *args, **options):
        try:
            spaces = Space.objects.all()

            if not spaces.exists():
                logger.info("No spaces found.")
                self.stdout.write(self.style.SUCCESS('No spaces found.'))
                return

            for space in spaces:
                try:
                    create_space_email_data_task_for_existing.delay(space.id)
                    logger.info(f"Triggered task for Space ID: {space.id}")
                except Exception as e:
                    logger.error(f"Error triggering task for Space ID: {space.id} - {str(e)}")
                    logger.error(traceback.format_exc())
                    continue

            self.stdout.write(self.style.SUCCESS('Successfully triggered tasks for all spaces'))

        except Exception as e:
            logger.error(f"Error in management command: {str(e)}")
            logger.error(traceback.format_exc())
            raise CommandError(f"Error in management command: {str(e)}")