import json
import logging
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import AITools
from django.db import models  # Import models directly

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate AI tools for each model definition'

    def handle(self, *args, **options):
        logger.info("Starting AI tool generation process.")
        try:
            with transaction.atomic():
                updated_count = self.create_or_update_ai_tools()
                if updated_count == 0:
                    logger.info("No AI tools needed updating.")
                else:
                    logger.info(f"{updated_count} AI tools updated or created.")
        except Exception as e:
            logger.error("Error during AI tool generation process.")
            logger.exception(e)
            raise

    def create_or_update_ai_tools(self):
        updated_count = 0
        # Loop over all models in all registered apps
        for model in apps.get_models():
            model_instance = model()  # Create an instance to access meta
            model_name = model_instance._meta.model_name  # Define model_name here
            if self.should_process(model):
                input_schema = self.generate_input_schema(model_instance)
                tool_name = f"{model_instance._meta.app_label}_{model_name}_tool"
                tool_description = f"Generate JSON for {model_instance._meta.app_label} {model_name}"

                # Create or update the AI Tool in the database
                ai_tool, created = AITools.objects.update_or_create(
                    name=tool_name,
                    defaults={
                        'description': tool_description,
                        'json_schema': json.dumps({
                            "name": tool_name,
                            "description": tool_description,
                            "input_schema": input_schema
                        }, indent=4)
                    }
                )
                if created:
                    logger.info(f"Created new AI Tool: {tool_name}")
                else:
                    logger.info(f"Updated existing AI Tool: {tool_name}")
                updated_count += 1
        return updated_count


    def generate_input_schema(self, model_instance):
        properties = {}
        required = []
        model_name = model_instance._meta.model_name
        for field in model_instance._meta.fields:
            if self.is_user_input_field(field.name):
                field_type = self.get_json_type(field)
                field_description = f"{field.verbose_name or field.name} for {model_name}"
                if isinstance(field, models.JSONField):
                    properties[field.name] = {
                        "type": "object",
                        "additionalProperties": True,
                        "description": field_description
                    }
                else:
                    properties[field.name] = {
                        "type": field_type,
                        "description": field_description
                    }
                required.append(field.name)  # Consider all user input fields as required

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def get_json_type(self, field):
        # Map Django field types to JSON schema types
        field_type_mapping = {
            models.CharField: "string",
            models.TextField: "string",
            models.IntegerField: "integer",
            models.BooleanField: "boolean",
            models.FloatField: "number",
            models.DateField: "string",
            models.DateTimeField: "string",
            models.JSONField: "object",
            models.ImageField: "string",
            models.FileField: "string",
        }
        for django_type, json_type in field_type_mapping.items():
            if isinstance(field, django_type):
                return json_type
        return "string"  # Default for custom or unsupported field types

    def is_user_input_field(self, field_name):
        excluded_names = ['id', 'created_at', 'updated_at', 'created_by']
        return field_name not in excluded_names

    def should_process(self, model):
        # List of known Django or third-party app labels to exclude
        excluded_app_labels = ['admin', 'auth', 'contenttypes', 'sessions', 'messages', 'migrations', 'staticfiles']
        return model._meta.app_label not in excluded_app_labels
