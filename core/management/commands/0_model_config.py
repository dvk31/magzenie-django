from django.core.management.base import BaseCommand
from core.models import ConfigurationItem
import logging
import traceback

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates all configuration items'

    def handle(self, *args, **options):
        try:
            ConfigurationItem.update_all_configurations()
            self.stdout.write(self.style.SUCCESS('Successfully updated all configurations'))
            logger.info("Configurations updated via management command")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating configurations: {str(e)}'))
            logger.error(f"Error updating configurations via management command: {str(e)}")
            logger.error(traceback.format_exc())