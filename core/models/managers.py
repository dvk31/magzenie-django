# core/managers.py

from django.db import models

class SoftDeleteManager(models.Manager):
    """
    Manager that excludes objects with a non-null deleted_at field.
    """
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)
