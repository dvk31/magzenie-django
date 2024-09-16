import json
import os
from django.core.management.base import BaseCommand
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

class Command(BaseCommand):
    help = 'Get all related objects for a given model in the format app_label.ModelName'

    def add_arguments(self, parser):
        parser.add_argument('model_name', type=str, help='The model name in app_label.ModelName format')

    def handle(self, *args, **kwargs):
        model_name = kwargs['model_name']

        try:
            app_label, model_name = model_name.split('.')
            model = apps.get_model(app_label, model_name)

            # Get an instance of the model to inspect relationships
            sample_instance = model.objects.first()
            if not sample_instance:
                self.stdout.write(self.style.ERROR(f"No instances of model {model_name} found."))
                return

            related_objects = self.get_related_objects(sample_instance)
            self.save_related_objects_to_file(app_label, model_name, related_objects)
        except ValueError:
            self.stderr.write(self.style.ERROR("model_name must be in the format app_label.ModelName"))
        except LookupError:
            self.stderr.write(self.style.ERROR(f"Model {model_name} not found."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(str(e)))

    def get_related_objects(self, obj):
        related_objects = {}
        for field in obj._meta.get_fields():
            if field.is_relation and field.related_model is not None:
                related_name = field.name
                if field.many_to_one or field.one_to_one:
                    related_objects[related_name] = {
                        'type': 'single',
                        'related_model': field.related_model.__name__,
                    }
                elif field.one_to_many or field.many_to_many:
                    related_objects[related_name] = {
                        'type': 'multiple',
                        'related_model': field.related_model.__name__,
                    }
        return related_objects

    def save_related_objects_to_file(self, app_label, model_name, related_objects):
        # Construct the file path outside the main project directory
        file_dir = os.path.join(settings.BASE_DIR, '..', app_label, 'models')
        file_name = f"{app_label.lower()}_{model_name.lower()}_related_objects.json"
        file_path = os.path.join(file_dir, file_name)
        
        os.makedirs(file_dir, exist_ok=True)
        
        with open(file_path, 'w') as json_file:
            json.dump(related_objects, json_file, indent=4)
        
        self.stdout.write(self.style.SUCCESS(f"Related objects saved to {file_path}"))