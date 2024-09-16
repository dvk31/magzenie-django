import json
import logging
import uuid
from django.core.management.base import BaseCommand, CommandError
from space.models.space_related_objects_handler import SpaceRelatedObjectsHandler

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Output all related object instance IDs for a given Space instance in JSON format.'

    def add_arguments(self, parser):
        parser.add_argument('space_id', type=uuid.UUID, help='UUID of the Space instance')

    def handle(self, *args, **options):
        space_id = options['space_id']

        logger.info(f"Fetching related objects for Space ID: {space_id}")
        handler = SpaceRelatedObjectsHandler(space_id=space_id)
        related_object_ids = handler.get_related_object_ids()

        if related_object_ids is None:
            self.stdout.write(self.style.ERROR(f"Failed to fetch related objects for Space ID: {space_id}"))
        else:
            self.stdout.write(self.style.SUCCESS(json.dumps(related_object_ids, indent=4)))