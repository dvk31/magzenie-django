import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from user.services.shopify_connection import ShopifyConnectionManager
from user.services.upload_video_file import upload_video_file
import hashlib

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Upload all video files from the root folder "tiktok" to Shopify'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip uploading files that already exist in Shopify',
        )

    def handle(self, *args, **options):
        tiktok_folder = os.path.join(settings.BASE_DIR, 'tiktok')
        if not os.path.exists(tiktok_folder):
            logger.error(f"The folder '{tiktok_folder}' does not exist.")
            self.stdout.write(self.style.ERROR(f"The folder '{tiktok_folder}' does not exist."))
            return

        video_files = [f for f in os.listdir(tiktok_folder) if f.endswith(('.mp4', '.mov', '.avi'))]
        
        if not video_files:
            logger.warning("No video files found in the tiktok folder.")
            self.stdout.write(self.style.WARNING("No video files found in the tiktok folder."))
            return

        skip_existing = options['skip_existing']

        with ShopifyConnectionManager() as manager:
            for video_file in video_files:
                self.upload_video(manager, os.path.join(tiktok_folder, video_file), skip_existing)

    def upload_video(self, manager, file_path, skip_existing):
        try:
            file_name = os.path.basename(file_path)
            
            # Generate a hash of the file content
            with open(file_path, 'rb') as file:
                file_hash = hashlib.md5(file.read()).hexdigest()
            
            logger.info(f"Processing {file_name} (Hash: {file_hash})...")
            self.stdout.write(f"Processing {file_name} (Hash: {file_hash})...")
            
            # Check if a file with this name already exists
            check_file_query = """
            query checkFile($filename: String!) {
              files(first: 1, query: $filename) {
                edges {
                  node {
                    ... on Video {
                      id
                      createdAt
                      alt
                      filename
                    }
                  }
                }
              }
            }
            """
            
            variables = {
                "filename": file_name
            }
            
            check_result = manager.execute_graphql_query(check_file_query, variables)
            
            if check_result.get('data', {}).get('files', {}).get('edges'):
                existing_file = check_result['data']['files']['edges'][0]['node']
                logger.info(f"File {file_name} already exists in Shopify:")
                logger.info(f"  ID: {existing_file['id']}")
                logger.info(f"  Created At: {existing_file['createdAt']}")
                logger.info(f"  Alt Text: {existing_file['alt']}")
                logger.info(f"  Filename: {existing_file['filename']}")
                if skip_existing:
                    self.stdout.write(self.style.WARNING(f"Skipped {file_name} (already exists)"))
                    return
                else:
                    self.stdout.write(self.style.WARNING(f"File {file_name} already exists, but uploading anyway as requested."))
            
            logger.info(f"Uploading {file_name}...")
            self.stdout.write(f"Uploading {file_name}...")
            
            result = upload_video_file(manager, file_path)
            
            if result:
                logger.info(f"Successfully uploaded {file_name}")
                self.stdout.write(self.style.SUCCESS(f"Successfully uploaded {file_name}"))
            else:
                logger.error(f"Failed to upload {file_name}")
                self.stdout.write(self.style.ERROR(f"Failed to upload {file_name}"))
        except Exception as e:
            logger.exception(f"Error processing {file_name}: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Error processing {file_name}: {str(e)}"))