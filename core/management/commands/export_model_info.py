import json
import logging
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db.models.fields.related import ForeignKey, OneToOneField, ManyToManyField
from django.db.models.fields import NOT_PROVIDED
from django.core.serializers.json import DjangoJSONEncoder
import datetime
# Set up logging
logger = logging.getLogger(__name__)

EXCLUDED_APPS = ['auth', 'contenttypes', 'sessions', 'token', 'admin', 'sites']


class Command(BaseCommand):
    help = 'Export model information as JSON'

    def handle(self, *args, **options):
        logger.info("Starting to export model information.")
        try:
            models_info = self.get_models_info()
            json_output = json.dumps(models_info, indent=4, cls=DjangoJSONEncoder)
            self.stdout.write(json_output)
            logger.info("Model information export completed successfully.")
        except Exception as e:
            logger.exception("An error occurred while exporting model information.")
            self.stderr.write("An error occurred. Please check the logs for more details.")

    def get_models_info(self):
        logger.info("Retrieving information for all models.")
        models_info = []
        for model in apps.get_models():
            # Skip models from excluded apps
            if model._meta.app_label not in EXCLUDED_APPS:
                models_info.append(self.get_model_info(model))
        logger.info("Information for all models retrieved successfully.")
        return models_info

    def get_model_info(self, model):
        model_dict = {
            'model': model.__name__,
            'app_label': model._meta.app_label,
            'fields': [self.get_field_info(field) for field in model._meta.get_fields()]
        }
        return model_dict

    def get_field_info(self, field):
        field_info = {
            'name': field.name,
            'type': field.get_internal_type(),
            'options': self.get_field_options(field)
        }
        if isinstance(field, (ForeignKey, OneToOneField, ManyToManyField)):
            field_info.update(self.get_relation_info(field))
        return field_info

    def get_relation_info(self, field):
        relation_info = {
            'related_model': self.get_related_model_name(field)
        }
        if isinstance(field, (ForeignKey, OneToOneField)):
            relation_info['options'] = {
                'on_delete': field.remote_field.on_delete.__name__,
                'null': field.null,
                'blank': field.blank
            }
        return relation_info

    def get_related_model_name(self, field):
        related_model = field.related_model
        if related_model:
            return f"{related_model._meta.app_label}.{related_model.__name__}"
        return None


    def get_field_options(self, field):
        options = {}
        for attr in ['null', 'blank', 'max_length', 'default', 'choices']:
            if hasattr(field, attr):
                value = getattr(field, attr)
                if value is NOT_PROVIDED:
                    value = None  # or some other placeholder indicating 'no default'
                elif callable(value):
                    try:
                        value = value()
                    except (TypeError, AttributeError):
                        value = "Callable default value (not serializable)"
                # Convert datetime objects to strings
                if isinstance(value, datetime.datetime):
                    value = value.isoformat()
                options[attr] = value
        return options

 