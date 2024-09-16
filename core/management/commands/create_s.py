import os
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generates serializers for specified Django apps'

    def handle(self, *args, **options):
        try:
            self.generate_serializers()
        except Exception as e:
            logger.error(f"Error generating serializers: {str(e)}")
            raise

    def generate_serializers(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        serializers_file_path = os.path.join(base_dir, 'serializers.py')

        with open(serializers_file_path, 'w') as file:
            file.write("from rest_framework import serializers\n")

            for app_name in settings.DJANGO_APPS:
                try:
                    app_config = apps.get_app_config(app_name)
                    models = app_config.get_models()
                    model_names = [model.__name__ for model in models]
                    if model_names:
                        file.write(f"from {app_config.name}.models import {', '.join(model_names)}\n")
                except LookupError:
                    logger.error(f"No models found or app is not recognized: {app_name}")
                    continue

            file.write("\n")

            for app_name in settings.DJANGO_APPS:
                try:
                    app_config = apps.get_app_config(app_name)
                    models = app_config.get_models()

                    for model in models:
                        model_name = model.__name__
                        fields = [field.name for field in model._meta.fields if not field.is_relation]
                        related_fields = [field.name for field in model._meta.fields if field.is_relation and not field.many_to_many]
                        many_to_many_fields = [field.name for field in model._meta.many_to_many]

                        file.write(f"class {model_name}Serializer(serializers.ModelSerializer):\n")

                        for rel_field in related_fields:
                            related_model = model._meta.get_field(rel_field).related_model
                            file.write(f"    {rel_field} = serializers.PrimaryKeyRelatedField(queryset={related_model.__name__}.objects.all(), write_only=True, required=False)\n")

                        for m2m_field in many_to_many_fields:
                            related_model = model._meta.get_field(m2m_field).related_model
                            file.write(f"    {m2m_field} = serializers.PrimaryKeyRelatedField(queryset={related_model.__name__}.objects.all(), many=True, required=False)\n")

                        file.write("    class Meta:\n")
                        file.write(f"        model = {model_name}\n")
                        file.write(f"        fields = {repr(fields + related_fields + many_to_many_fields)}\n")

                        file.write("\n")
                except LookupError:
                    logger.error(f"Failed to load models for app: {app_name}")
                    continue

        logger.info(f"Serializers generated successfully at {serializers_file_path}.")