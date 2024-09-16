# digital_setup/models.py
from django.db import models
from django.conf import settings
from core.models import BaseModel
from magazines.models import Magazine

class DigitalSettings(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='digital_settings')
    enable_kiosk_mode = models.BooleanField(default=False)
    auto_launch_magazine = models.BooleanField(default=False)
    selected_magazine = models.ForeignKey(Magazine, on_delete=models.SET_NULL, null=True, blank=True, related_name='digital_settings')

    def __str__(self):
        return f"DigitalSettings {self.id} for {self.user.email}"