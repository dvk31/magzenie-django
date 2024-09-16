# core/management/commands/generate_model_json.py
import json
import logging
from django.apps import apps
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models
from django.contrib import admin
from django.core.validators import MinValueValidator, MaxValueValidator

import inspect

logger = logging.getLogger(__name__)

import json


from django.utils.functional import Promise
from django.utils.encoding import force_str

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_str(obj)  # Convert lazy translation objects to string
        if callable(obj):
            return f"Callable: {obj.__name__}"  # Return function name for callable objects
        return json.JSONEncoder.default(self, obj)

class Command(BaseCommand):
    help = 'Generates JSON output of Django models for specified apps'

    def handle(self, *args, **options):
        output_file = 'core/jsonmodel.json'
        try:
            model_data = self.get_model_data()
            self.generate_json_file(model_data, output_file)
            self.stdout.write(self.style.SUCCESS('JSON file generated successfully'))
        except Exception as e:
            logger.exception('An error occurred while generating JSON')
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))
            raise

    def get_model_data(self):
        model_data = {}
        for app_name in settings.DJANGO_APPS:
            app_models = apps.get_app_config(app_name).get_models()
            for model in app_models:
                model_name = model.__name__
                model_data[model_name] = {
                    'fields': self.get_model_fields(model),
                    'methods': self.get_model_methods(model),
                    'meta': self.get_model_meta(model),
                    'relationships': self.get_model_relationships(model),
                    #'custom_managers': self.get_custom_managers(model),
                    'str_method': self.get_str_method(model),
                    'inheritance': self.get_model_inheritance(model),
                    'permissions': self.get_model_permissions(model),
                    'ordering': self.get_model_ordering(model),
                    'constraints': self.get_model_constraints(model),
                    'options': self.get_model_options(model),
                    'managers': self.get_model_managers(model),
                    #'signals': self.get_model_signals(model),
                    #'admin': self.get_model_admin(model),
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
            'choices': field.choices,
            'upload_to': field.upload_to if isinstance(field, models.FileField) else None,
            'primary_key': field.primary_key,
            'unique': field.unique,
            'default': field.default,
            'editable': field.editable,
            'hidden': field.hidden,
        }
        if isinstance(field, models.ForeignKey) or isinstance(field, models.OneToOneField):
            field_data['related_model'] = field.related_model.__name__
            field_data['on_delete'] = field.remote_field.on_delete.__name__
            if isinstance(field, models.ForeignKey):
                field_data['type'] = 'ForeignKey'
                field_data['related_name'] = field.remote_field.related_name
            else:
                field_data['type'] = 'OneToOneField'
        else:
            self.get_field_specific_data(field, field_data)
        return field_data

    def get_field_specific_data(self, field, field_data):
        if isinstance(field, models.CharField) or isinstance(field, models.TextField):
            field_data['max_length'] = field.max_length
        elif isinstance(field, models.DecimalField):
            field_data['max_digits'] = field.max_digits
            field_data['decimal_places'] = field.decimal_places
        elif isinstance(field, models.IntegerField):
            self.get_integer_field_validators(field, field_data)
        field_data['help_text'] = field.help_text
        field_data['blank'] = field.blank
        field_data['null'] = field.null

    def get_integer_field_validators(self, field, field_data):
        validators = field.validators
        for validator in validators:
            if isinstance(validator, MinValueValidator):
                field_data['min_value'] = validator.limit_value
            elif isinstance(validator, MaxValueValidator):
                field_data['max_value'] = validator.limit_value

    def get_model_methods(self, model):
        methods = {}
        for method_name in dir(model):
            method = getattr(model, method_name)
            if callable(method) and not method_name.startswith('_'):
                methods[method_name] = self.get_method_data(method)
        return methods

    def get_method_data(self, method):
        method_data = {
            'parameters': [],
            'return_type': 'None',
            'description': method.__doc__ or '',
            'is_class_method': inspect.ismethod(method),
            'is_static_method': isinstance(method, staticmethod),
        }
        
        if not inspect.isbuiltin(method):
            try:
                signature = inspect.signature(method)
                method_data['return_type'] = signature.return_annotation.__name__ if signature.return_annotation is not inspect.Signature.empty else 'None'
                
                for param_name, param in signature.parameters.items():
                    if param_name != 'self':
                        method_data['parameters'].append({
                            'name': param_name,
                            'type': param.annotation.__name__ if param.annotation is not inspect.Parameter.empty else 'Any',
                            'description': '',
                        })
            except (ValueError, TypeError):
                pass
        
        return method_data

    def get_model_meta(self, model):
        return {
            'verbose_name': model._meta.verbose_name,
            'verbose_name_plural': model._meta.verbose_name_plural,
            'db_table': model._meta.db_table,
            'app_label': model._meta.app_label,
            'get_latest_by': model._meta.get_latest_by,
            'order_with_respect_to': model._meta.order_with_respect_to,
            'abstract': model._meta.abstract,
            'managed': model._meta.managed,
            'proxy': model._meta.proxy,
        }

    def get_model_relationships(self, model):
        relationships = {
            'one_to_one': [],
            'one_to_many': [],
            'many_to_many': [],
        }
        for field in model._meta.get_fields():
            if isinstance(field, models.OneToOneField):
                relationships['one_to_one'].append({
                    'field': field.name,
                    'related_model': field.related_model.__name__,
                })
            elif isinstance(field, models.ForeignKey):
                relationships['one_to_many'].append({
                    'field': field.name,
                    'related_model': field.related_model.__name__,
                })
            elif isinstance(field, models.ManyToManyField):
                relationships['many_to_many'].append({
                    'field': field.name,
                    'related_model': field.related_model.__name__,
                })
        return relationships

    def get_custom_managers(self, model):
        custom_managers = []
        for manager_name, manager in model._meta.managers_map.items():
            if manager.__class__.__name__ != 'Manager':
                custom_managers.append(self.get_custom_manager_data(manager))
        return custom_managers

    def get_custom_manager_data(self, manager):
        custom_manager_data = {
            'manager_name': manager.__class__.__name__,
            'methods': []
        }
        for method_name in dir(manager):
            method = getattr(manager, method_name)
            if callable(method) and not method_name.startswith('_'):
                custom_manager_data['methods'].append(self.get_method_data(method))
        return custom_manager_data


    def get_str_method(self, model):
        return {
            'description': model.__str__.__doc__ or '',
            'return_type': 'str',
            'implementation': inspect.getsource(model.__str__).strip(),
        }

    def get_model_inheritance(self, model):
        inheritance = {
            'type': None,
            'parents': [],
        }
        if model.__base__ != models.Model:
            inheritance['type'] = 'abstract' if model._meta.abstract else 'multi-table'
            inheritance['parents'] = [parent.__name__ for parent in model._meta.parents]
        if model._meta.proxy:
            inheritance['type'] = 'proxy'
            inheritance['parents'] = [model.__base__.__name__]
        return inheritance

    def get_model_permissions(self, model):
        return {
            'default_permissions': list(model._meta.default_permissions),
            'custom_permissions': [(perm[0], perm[1]) for perm in model._meta.permissions],
        }

    def get_model_ordering(self, model):
        return {
            'default_ordering': list(model._meta.ordering),
            'get_latest_by': model._meta.get_latest_by,
            'order_with_respect_to': model._meta.order_with_respect_to,
        }

    def get_model_constraints(self, model):
        return {
            'unique_together': [list(fields) for fields in model._meta.unique_together],
            'index_together': [list(fields) for fields in model._meta.index_together],
        }

    def get_model_options(self, model):
        return {
            'db_table': model._meta.db_table,
            'app_label': model._meta.app_label,
            'verbose_name': model._meta.verbose_name,
            'verbose_name_plural': model._meta.verbose_name_plural,
            'get_latest_by': model._meta.get_latest_by,
            'order_with_respect_to': model._meta.order_with_respect_to,
            'abstract': model._meta.abstract,
            'managed': model._meta.managed,
            'proxy': model._meta.proxy,
        }

    def get_model_managers(self, model):
        return {
            'default_manager': model._meta.default_manager.__class__.__name__,
            'custom_managers': [manager.__class__.__name__ for manager in model._meta.managers],
        }

    def get_model_signals(self, model):
        signals = {
            'pre_save': [],
            'post_save': [],
            'pre_delete': [],
            'post_delete': [],
        }
        for receiver in models.signals.pre_save.receivers:
            if isinstance(receiver, tuple):
                receiver_fn = receiver[1]()  # Dereference the weak reference
                if receiver_fn and hasattr(receiver_fn, '__qualname__') and receiver_fn.__qualname__.startswith(model.__name__ + '.'):
                    signals['pre_save'].append(receiver_fn.__name__)
            elif hasattr(receiver, '__self__') and receiver.__self__ == model:
                signals['pre_save'].append(receiver.__name__)
        for receiver in models.signals.post_save.receivers:
            if isinstance(receiver, tuple):
                receiver_fn = receiver[1]()  # Dereference the weak reference
                if receiver_fn and hasattr(receiver_fn, '__qualname__') and receiver_fn.__qualname__.startswith(model.__name__ + '.'):
                    signals['post_save'].append(receiver_fn.__name__)
            elif hasattr(receiver, '__self__') and receiver.__self__ == model:
                signals['post_save'].append(receiver.__name__)
        for receiver in models.signals.pre_delete.receivers:
            if isinstance(receiver, tuple):
                receiver_fn = receiver[1]()  # Dereference the weak reference
                if receiver_fn and hasattr(receiver_fn, '__qualname__') and receiver_fn.__qualname__.startswith(model.__name__ + '.'):
                    signals['pre_delete'].append(receiver_fn.__name__)
            elif hasattr(receiver, '__self__') and receiver.__self__ == model:
                signals['pre_delete'].append(receiver.__name__)
        for receiver in models.signals.post_delete.receivers:
            if isinstance(receiver, tuple):
                receiver_fn = receiver[1]()  # Dereference the weak reference
                if receiver_fn and hasattr(receiver_fn, '__qualname__') and receiver_fn.__qualname__.startswith(model.__name__ + '.'):
                    signals['post_delete'].append(receiver_fn.__name__)
            elif hasattr(receiver, '__self__') and receiver.__self__ == model:
                signals['post_delete'].append(receiver.__name__)
        return signals

    def get_model_admin(self, model):
        model_admin = admin.site._registry.get(model)
        if model_admin:
            return {
                'list_display': list(model_admin.list_display) if model_admin.list_display else [],
                'list_filter': list(model_admin.list_filter) if model_admin.list_filter else [],
                'search_fields': list(model_admin.search_fields) if model_admin.search_fields else [],
                'ordering': list(model_admin.ordering) if model_admin.ordering else [],
                'readonly_fields': list(model_admin.readonly_fields) if model_admin.readonly_fields else [],
                'inlines': [inline.__name__ for inline in model_admin.inlines] if model_admin.inlines else [],
            }
        return None

    def generate_json_file(self, model_data, output_file):
        with open(output_file, 'w') as f:
            json.dump(model_data, f, indent=4, cls=CustomJSONEncoder)