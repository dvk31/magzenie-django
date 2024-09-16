from django.db import models
from core.models import BaseModel

class Role(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    permissions = models.JSONField(default=dict, null=True, blank=True)
    shopify_id = models.CharField(max_length=255, unique=True, null=True, blank=True)

    def __str__(self):
        return f"Role: {self.name}"