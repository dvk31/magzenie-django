import json
import os
from django.core.management.base import BaseCommand
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from tryoutcms.models import  File, ResourceContent, Resource, CheckInType, CheckIn
import logging
import csv
#from .ai_service import AIService
import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process a CSV file and create/update ResourceContent and associated Resource'

    def add_arguments(self, parser):
        parser.add_argument('file_id', type=str, help='ID of the file to process')

    def handle(self, *args, **options):
        file_id = options['file_id']
        all_rows_processed_successfully = True  # Initialize the flag
        try:
            file = self.get_file(file_id)
            if self.check_if_already_processed(file):
                return

            header_mappings = self.get_header_mappings()
            self.process_csv(file, header_mappings)
            # Only mark as processed if all rows were successful
            if all_rows_processed_successfully:
                self.mark_file_as_processed(file)
            self.stdout.write(self.style.SUCCESS(f'Successfully processed file with ID: {file_id}'))
        except Exception as e:
            all_rows_processed_successfully = False  # Set the flag to False if an exception occurs
            self.stderr.write(self.style.ERROR(f'Error processing file with ID {file_id}: {e}'))

    def get_file(self, file_id):
        try:
            return File.objects.get(file_id=file_id)
        except File.DoesNotExist:
            message = f'File with ID {file_id} does not exist.'
            self.stderr.write(self.style.ERROR(message))
            logger.error(message)
            raise

    def check_if_already_processed(self, file):
        if file.is_gpt_processed:
            message = f'File with ID {file.file_id} has already been processed.'
            self.stdout.write(self.style.WARNING(message))
            logger.warning(message)
            return True
        return False

    def read_file_header(self, file):
        if not file.file:
            message = f'File with ID {file.file_id} has no uploaded file.'
            self.stderr.write(self.style.ERROR(message))
            logger.error(message)
            raise ValueError(message)

        try:
            with file.file.open('r') as f:
                reader = csv.reader(f)
                header = next(reader)  # Read only the first line (header)
            return header
        except Exception as e:
            message = f'Error reading header from file with ID {file.file_id}: {e}'
            self.stderr.write(self.style.ERROR(message))
            logger.error(message, exc_info=True)
            raise

            
    def get_header_mappings(self):
        return {
            "Title": "title",
            "Source/Author": "source_author",
            "Description": "description",
            "Link": "link",
            "Words": "words",
            "Duration": "duration",
            "Content Type": "content_type",
            "Content Stub": "content_stub",
            "Cover Image": "cover_image",
            # Note: We will handle 'Pre-Program Key Result', 'Check In Question 1', and 'Check In Question 2' separately
        }

    def process_csv(self, file, header_mappings):
        all_rows_processed_successfully = True  # Initialize the flag to True

        with file.file.open('r') as f:
            reader = csv.reader(f)
            headers = next(reader)  # Read the header row

            for row_number, row in enumerate(reader, start=1):
                try:
                    resource_content_data = self.map_row_to_resource_content(headers, row, header_mappings, row_number)
                    resource_content = self.create_or_update_resource_content(file, resource_content_data, row_number)
                    
                    # Associate with resource
                    resource = self.associate_with_resource(resource_content)
                    
                    # Handle check-ins
                    self.create_check_ins(row, headers, resource_content, row_number)
                except Exception as e:
                    all_rows_processed_successfully = False  # Set the flag to False upon error
                    self.stderr.write(self.style.ERROR(f'Failed to process row {row_number} of file {file.file_id}: {e}'))
                    logger.error(f'Failed to process row {row_number} of file {file.file_id}: {e}', exc_info=True)

        # Only mark the file as processed if all rows were processed successfully
        if all_rows_processed_successfully:
            self.mark_file_as_processed(file)

    def create_check_ins(self, row, headers, resource_content, row_number):
        # Ensure that the CheckInType 'Question' exists
        check_in_type, _ = CheckInType.objects.get_or_create(name='Question')
        
        for i, header in enumerate(headers):
            if 'Check In Question' in header:
                question = row[i].strip()
                if question:  # Only create a CheckIn if there's a question in the CSV
                    CheckIn.objects.create(
                        resource_content=resource_content,
                        check_in_type=check_in_type,
                        title=question
                    )

    def map_row_to_resource_content(self, headers, row, header_mappings, row_number):
        resource_content_data = {}
        # Normalize the headers for comparison
        normalized_headers = {header.strip().lower(): index for index, header in enumerate(headers)}
        
        for csv_header, model_field in header_mappings.items():
            normalized_csv_header = csv_header.strip().lower()
            if normalized_csv_header in normalized_headers:
                header_index = normalized_headers[normalized_csv_header]
                # Some fields like 'words' and 'duration' should be integers
                if model_field in ['words', 'duration']:
                    resource_content_data[model_field] = self.parse_integer(row[header_index])
                else:
                    resource_content_data[model_field] = row[header_index].strip() if row[header_index].strip() else None
            else:
                logger.warning(f"Missing or invalid CSV header '{csv_header}' in row {row_number}")
                resource_content_data[model_field] = None
        logger.info(f"Extracted data for row {row_number}: {resource_content_data}")
        return resource_content_data

    def parse_integer(self, value):
        try:
            return int(value) if value.strip() else None
        except (ValueError, AttributeError):
            return None

    def parse_integer(self, value):
        try:
            return int(value) if value.strip() else None
        except (ValueError, AttributeError):
            return None


    
    def create_or_update_resource_content(self, file, resource_content_data, row_number):
        try:
            # Use 'link' as the unique field to identify the ResourceContent instance
            unique_field = 'link'
            unique_value = resource_content_data[unique_field]

            # Check if a ResourceContent instance already exists for the given File and link
            resource_content = ResourceContent.objects.filter(file=file, link=unique_value).first()

            if resource_content:
                # Update the existing ResourceContent instance
                for key, value in resource_content_data.items():
                    setattr(resource_content, key, value)
                resource_content.save()
                action = 'Updated'
            else:
                # Create a new ResourceContent instance
                resource_content = ResourceContent.objects.create(file=file, **resource_content_data)
                action = 'Created'

            logger.info(f"{action} ResourceContent instance for row {row_number} of file {file.file_id}")
            return resource_content
        except Exception as e:
            logger.error(f"Failed to create or update ResourceContent for row {row_number} of file {file.file_id}. Error: {e}", exc_info=True)
            raise
            
    def associate_with_resource(self, resource_content):
        # Attempt to find an existing Resource by title
        try:
            resource = Resource.objects.get(title=resource_content.title)
        except Resource.DoesNotExist:
            # If the Resource does not exist, create a new one without a Tryout instance
            resource = Resource.objects.create(title=resource_content.title)

        # Associate the ResourceContent with the found or created Resource
        resource.content_items.add(resource_content)

        return resource

        

    def mark_file_as_processed(self, file):
            file.is_gpt_processed = True
            file.save()