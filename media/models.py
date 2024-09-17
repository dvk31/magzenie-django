# media/models.py
from django.db import models
from django.conf import settings
from core.models import BaseModel

class Media(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='uploaded_media/')
    media_url = models.URLField()

    def __str__(self):
        return f"Media {self.id} uploaded by {self.user.email}"