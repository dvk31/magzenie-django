import json
import logging
import types
import inspect
from django.apps import apps
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models
from django.contrib import admin
import inspect
# Set up logging
logging.basicConfig(level=logging.DEBUG, filename='generate_model_json.log', filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')

import json
import inspect
import types

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # Handle functions and methods
        if callable(obj):
            return f"Callable: {obj.__name__}"

        # Handle inspect.Parameter objects specifically
        if isinstance(obj, inspect.Parameter):
            return {
                'name': obj.name,
                'kind': obj.kind.name,
                'default': self.default(obj.default) if obj.default is not inspect.Parameter.empty else 'No default',
                'annotation': self.default(obj.annotation) if obj.annotation is not inspect.Parameter.empty else 'No annotation'
            }

        # Try to serialize other objects that are typically not serializable
        try:
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            elif hasattr(obj, '__slots__'):
                return {slot: getattr(obj, slot) for slot in obj.__slots__ if hasattr(obj, slot)}
            else:
                return str(obj)
        except TypeError:
            pass

        # Fallback to the superclass method
        return super().default(obj)


class Command(BaseCommand):
    help = 'Generates JSON output of Django models for specified apps'

    def handle(self, *args, **options):
        output_file = 'core/jsonmodel.json'
        try:
            model_data = self.get_model_data()
            self.generate_json_file(model_data, output_file)
            self.stdout.write(self.style.SUCCESS('JSON file generated successfully'))
        except Exception as e:
            logging.exception("An error occurred")
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))
            raise

    def get_model_data(self):
        model_data = {}
        for app_name in settings.DJANGO_APPS:
            app_models = apps.get_app_config(app_name).get_models()
            for model in app_models:
                model_name = model.__name__
                model_data[model_name] = {
                    'app_label': model._meta.app_label,
                    'model_name': model_name,
                    'fields': self.get_model_fields(model),
                    'methods': self.get_model_methods(model),
                    'meta': self.get_model_meta(model),
                    'relationships': self.get_relationships(model),
                    'str_method': self.get_str_method(model),
                    'custom_managers': self.get_custom_managers(model)
                }
        return model_data

    def get_model_fields(self, model):
        fields = {}
        for field in model._meta.fields:
            field_data = self.get_field_data(field)
            fields[field.name] = field_data
        return fields

    def get_field_data(self, field):
        field_data = {
            'type': field.get_internal_type(),
            'required': not field.null,
        }
        if field.is_relation:
            field_data['related_model'] = field.related_model.__name__
            if isinstance(field, models.ForeignKey):
                field_data['type'] = 'ForeignKey'
                field_data['related_name'] = field.remote_field.related_name
                field_data['on_delete'] = field.remote_field.on_delete.__name__
        else:
            self.get_field_specific_data(field, field_data)
        return field_data

    def get_field_specific_data(self, field, field_data):
        if isinstance(field, (models.CharField, models.TextField)):
            field_data['max_length'] = field.max_length
        field_data['default'] = "Callable" if callable(field.default) else field.default
        field_data['null'] = field.null
        field_data['blank'] = field.blank

    def get_model_methods(self, model):
        methods = {}
        for name, method in inspect.getmembers(model, predicate=inspect.isfunction):
            if method.__module__ == model.__module__:
                methods[name] = {
                    'description': method.__doc__,
                    'parameters': inspect.signature(method).parameters
                }
        return methods

    def get_model_meta(self, model):
        return {
            'verbose_name': model._meta.verbose_name,
            'verbose_name_plural': model._meta.verbose_name_plural
        }

   

    def get_str_method(self, model):
        str_method = getattr(model, '__str__', None)
        if str_method and callable(str_method):
            return {
                'description': str_method.__doc__ or "Returns a string representation of the model.",
                'return_type': 'str',
                'implementation': inspect.getsource(str_method)
            }
        return None

    def get_custom_managers(self, model):
        custom_managers = []
        for manager_name in dir(model):
            manager = getattr(model, manager_name)
            if hasattr(manager, 'objects') and hasattr(manager.objects, '__class__'):
                methods = []
                for method_name in dir(manager.objects.__class__):
                    if callable(getattr(manager.objects.__class__, method_name)) and not method_name.startswith('_'):
                        method = getattr(manager.objects.__class__, method_name)
                        if method.__module__ == manager.__module__:
                            methods.append({
                                'method_name': method_name,
                                'parameters': [param.name for param in inspect.signature(method).parameters.values()],
                                'return_type': str(inspect.signature(method).return_type),
                                'description': method.__doc__
                            })
                custom_managers.append({
                    'manager_name': manager_name,
                    'methods': methods
                })
        return custom_managers

    def get_relationships(self, model):
        relationships = {'one_to_one': [], 'one_to_many': [], 'many_to_many': []}
        for field in model._meta.get_fields():
            if isinstance(field, models.OneToOneField):
                relationships['one_to_one'].append({
                    'field': field.name,
                    'related_model': field.related_model.__name__
                })
            elif isinstance(field, models.ForeignKey):
                relationships['one_to_many'].append({
                    'field': field.name,
                    'related_model': field.related_model.__name__
                })
            elif isinstance(field, models.ManyToManyField):
                relationships['many_to_many'].append({
                    'field': field.name,
                    'related_model': field.related_model.__name__
                })
        return relationships


    def generate_json_file(self, model_data, output_file):
        try:
            output_data = {}
            for model_name, data in model_data.items():
                output_data[model_name] = {
                    'app_label': data['app_label'],
                    'model_name': data['model_name'],
                    'data': data
                }
            with open(output_file, 'w') as f:
                json.dump(output_data, f, cls=CustomJSONEncoder, indent=4)
            self.stdout.write(self.style.SUCCESS(f'JSON file successfully written to {output_file}'))
        except IOError as e:
            self.stderr.write(self.style.ERROR(f'Failed to write JSON file: {e}'))
            raise