# analytics/models.py
from django.db import models
from django.conf import settings
from core.models import BaseModel
from magazines.models import Page

class PageView(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='views')
    timestamp = models.DateTimeField(auto_now_add=True)
    device_type = models.CharField(max_length=50)
    duration = models.IntegerField()

    def __str__(self):
        return f"PageView {self.id} on Page {self.page.id} at {self.timestamp}"