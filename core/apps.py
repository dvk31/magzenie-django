# core/apps.py
from django.apps import AppConfig
from django.conf import settings

class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from django.apps import apps
        from django.db.models import Model

        DJANGO_APPS = getattr(settings, 'DJANGO_APPS', [])
        TOOLS_SCHEMA_APPS = getattr(settings, 'TOOLS_SCHEMA_APPS', [])

        DJANGO_MODELS = {}
        for app_name in DJANGO_APPS + TOOLS_SCHEMA_APPS:
            app_models = apps.get_app_config(app_name).get_models()
            for model in app_models:
                if issubclass(model, Model):
                    # Ensure only model classes are processed
                    table_name = model._meta.db_table
                    columns = [field.name for field in model._meta.fields]
                    DJANGO_MODELS[table_name] = {'columns': columns}

        setattr(settings, 'DJANGO_MODELS', DJANGO_MODELS)