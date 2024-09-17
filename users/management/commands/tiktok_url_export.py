# your_app/management/commands/import_tiktok_videos.py

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from core.models import TikTokVideo  
import csv
from datetime import datetime
import os
import pytz

class Command(BaseCommand):
    help = 'Import TikTok videos from a CSV file in the root directory'

    def handle(self, *args, **options):
        csv_file_path = os.path.join(os.getcwd(), 'tiktok_videos.csv')
        
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'CSV file not found at {csv_file_path}'))
            return

        with open(csv_file_path, 'r') as file:
            reader = csv.DictReader(file)
            videos_created = 0
            videos_skipped = 0

            for row in reader:
                try:
                    # Check if a video with this URL already exists
                    if TikTokVideo.objects.filter(tiktok_video_url=row['tiktok_video_url']).exists():
                        videos_skipped += 1
                        continue

                    # Parse the datetime string and make it timezone-aware
                    created_at = self.parse_datetime(row['created_at'])
                    updated_at = self.parse_datetime(row['updated_at'])

                    TikTokVideo.objects.create(
                        tiktok_video_url=row['tiktok_video_url'],
                        downloaded_video_url=row['downloaded_video_url'] or None,
                        ai_processed=row['ai_processed'].lower() == 'true',
                        transcription=row['transcription'] or None,
                        generated_caption=row['generated_caption'] or None,
                        created_at=created_at,
                        updated_at=updated_at
                    )
                    videos_created += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error processing row: {row}. Error: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {videos_created} videos. Skipped {videos_skipped} existing videos.'))

    def parse_datetime(self, datetime_str):
        # Parse the datetime string and make it timezone-aware
        dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S.%f+00')
        return pytz.utc.localize(dt)