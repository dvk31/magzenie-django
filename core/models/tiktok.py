# In your app's models.py file
from django.db import models

class TikTokVideo(models.Model):
    tiktok_video_url = models.URLField(unique=True)
    downloaded_video_url = models.URLField(null=True, blank=True)
    ai_processed = models.BooleanField(default=False)
    transcription = models.TextField(null=True, blank=True)
    generated_caption = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.tiktok_video_url