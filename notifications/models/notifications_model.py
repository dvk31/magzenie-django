
from django.db import models
from django.conf import settings
from core.models import BaseModel


class NotificationPreferences(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    email_notifications = models.JSONField(default=dict)
    sms_notifications = models.JSONField(default=dict)

    def __str__(self):
        return f"NotificationPreferences {self.id} for {self.user.email}"

class Notification(BaseModel):
    NOTIFICATION_TYPES = [
        ('Message', 'Message'),
        ('Alert', 'Alert'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification {self.id}: {self.type} for {self.user.email} at {self.timestamp}"