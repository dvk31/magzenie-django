# django/user/management/commands/tiktok_download.py
import os
import yt_dlp
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import TikTokVideo

class Command(BaseCommand):
    help = 'Download TikTok videos for entries in the database'

    def handle(self, *args, **options):
        # Create a 'tiktok' folder in the root directory if it doesn't exist
        download_path = os.path.join(settings.BASE_DIR, 'tiktok')
        os.makedirs(download_path, exist_ok=True)

        # Get all TikTok videos that haven't been downloaded yet
        videos_to_download = TikTokVideo.objects.filter(downloaded_video_url__isnull=True)

        self.stdout.write(f"Found {videos_to_download.count()} videos to download.")

        for video in videos_to_download:
            try:
                self.download_video(video, download_path)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error downloading video {video.id}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("Finished downloading videos."))

    def download_video(self, video, download_path):
        ydl_opts = {
            'outtmpl': os.path.join(download_path, f'%(id)s.%(ext)s'),
            'format': 'best',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video.tiktok_video_url, download=True)
            filename = ydl.prepare_filename(info)
            
            # Update the database with the downloaded video URL
            relative_path = os.path.relpath(filename, settings.BASE_DIR)
            video.downloaded_video_url = relative_path
            video.save()

            self.stdout.write(self.style.SUCCESS(f"Successfully downloaded video {video.id}"))