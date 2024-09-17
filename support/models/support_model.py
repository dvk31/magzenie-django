# support/models.py
from django.db import models
from django.conf import settings
from core.models import BaseModel

class FAQ(BaseModel):
    CATEGORY_CHOICES = [
        ('General', 'General'),
        ('Technical', 'Technical'),
        ('Billing', 'Billing'),
        ('Print Orders', 'Print Orders'),
        ('Other', 'Other'),
    ]

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    question = models.CharField(max_length=255)
    answer = models.TextField()

    def __str__(self):
        return f"FAQ {self.id}: {self.question} in {self.category}"

class HelpArticle(BaseModel):
    title = models.CharField(max_length=255)
    content = models.TextField()
    snippet = models.CharField(max_length=500)

    def __str__(self):
        return f"HelpArticle {self.id}: {self.title}"

class SupportTicket(BaseModel):
    CATEGORY_CHOICES = [
        ('Technical Issue', 'Technical Issue'),
        ('Billing', 'Billing'),
        ('Print Orders', 'Print Orders'),
        ('Other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
        ('Closed', 'Closed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    attachments = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    response = models.TextField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"SupportTicket {self.id}: {self.subject} by {self.user.email}"