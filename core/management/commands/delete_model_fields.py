from django.core.management.base import BaseCommand
from webhook.models import ModelField

class Command(BaseCommand):
    help = 'Delete all ModelField objects'

    def handle(self, *args, **kwargs):
        # Delete all ModelField objects
        deleted_count = ModelField.objects.all().delete()[0]

        if deleted_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} ModelField objects.'))
        else:
            self.stdout.write(self.style.WARNING('No ModelField objects found to delete.'))