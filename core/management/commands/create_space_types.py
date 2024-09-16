import json
import traceback
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from django.db.utils import IntegrityError
from space.models import SpaceTypeJson, SpaceType, IndustryType, SpaceTemplate  # Adjust the import based on your actual app structure
import os

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Populate SpaceType, IndustryType, and SpaceTemplate from a JSON file'

    def get_json_file_path(self):
        return os.path.join(settings.BASE_DIR, '..', 'space', 'models', 'space_types.json')

    def handle(self, *args, **options):
        json_file_path = self.get_json_file_path()
        try:
            with open(json_file_path, 'r') as file:
                data = json.load(file)
        except FileNotFoundError:
            logger.error(f"File {json_file_path} not found.")
            self.stderr.write(self.style.ERROR(f"File {json_file_path} not found."))
            return
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {str(e)}")
            self.stderr.write(self.style.ERROR(f"Error decoding JSON: {str(e)}"))
            return

        try:
            with transaction.atomic():
                self.populate_space_type_json(json_file_path, data)
                self.populate_space_data(data)
        except Exception as e:
            logger.error(f"Error during population: {str(e)}")
            logger.error(traceback.format_exc())
            self.stderr.write(self.style.ERROR(f"Error during population: {str(e)}"))
            self.stderr.write(self.style.ERROR(traceback.format_exc()))


    def populate_space_type_json(self, json_file, data):
        try:
            space_type_json, created = SpaceTypeJson.objects.update_or_create(
                name=json_file,
                defaults={'data': data}
            )
            if created:
                logger.info(f"Created SpaceTypeJson entry for {json_file}")
            else:
                logger.info(f"Updated SpaceTypeJson entry for {json_file}")
        except IntegrityError as e:
            logger.error(f"Integrity error while saving SpaceTypeJson: {str(e)}")
            raise

    def populate_space_data(self, data):
        for space_type_data in data.get('space_types', []):
            space_type, created = SpaceType.objects.update_or_create(
                name=space_type_data['name'],
                defaults={'description': space_type_data['description']}
            )
            if created:
                logger.info(f"Created SpaceType: {space_type.name}")
            else:
                logger.info(f"Updated SpaceType: {space_type.name}")

            for template_data in space_type_data.get('templates', []):
                SpaceTemplate.objects.update_or_create(
                    space_type=space_type,
                    industry_type=None,
                    defaults={'template': template_data['template']}
                )

            for industry_data in space_type_data.get('industries', []):
                industry_type, created = IndustryType.objects.update_or_create(
                    name=industry_data['name'],
                    space_type=space_type,
                    defaults={'description': industry_data['description']}
                )
                if created:
                    logger.info(f"Created IndustryType: {industry_type.name}")
                else:
                    logger.info(f"Updated IndustryType: {industry_type.name}")

                for template_data in industry_data.get('templates', []):
                    SpaceTemplate.objects.update_or_create(
                        space_type=space_type,
                        industry_type=industry_type,
                        defaults={'template': template_data['template']}
                    )