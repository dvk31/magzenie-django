from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from webhook.models import ModelField

class Command(BaseCommand):
    help = 'Populate ModelField entries based on existing models and their content types'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('Populating ModelField entries...'))
        for model in apps.get_models():
            content_type = ContentType.objects.get_for_model(model)
            field_names = [field.name for field in model._meta.get_fields()]
            for field_name in field_names:
                model_field, created = ModelField.objects.get_or_create(content_type=content_type, field_name=field_name)
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created ModelField: {model_field}'))
                else:
                    self.stdout.write(self.style.WARNING(f'ModelField already exists: {model_field}'))
        self.stdout.write(self.style.SUCCESS('ModelField population completed.'))
