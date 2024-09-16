import json
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from core.models import ModelDefinition, AITools

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
                    logger.info(f"AI tool generation process completed successfully. {updated_count} tools updated.")
        except Exception as e:
            logger.error("Error during AI tool generation process.")
            logger.exception(e)
            raise

    def create_or_update_ai_tools(self):
        model_definitions = ModelDefinition.objects.all()
        updated_count = 0
        for model_def in model_definitions:
            self.process_model_definition(model_def)
            model_def.last_run = timezone.now()
            model_def.save()
            logger.info(f"Processed {model_def.app_name}.{model_def.model_name}. Last updated: {model_def.last_updated}, Last run: {model_def.last_run}")
            updated_count += 1
        return updated_count

    def should_process(self, model_def):
        # Check if never run or if updated after last run
        if not model_def.last_run:
            return True
        if model_def.last_updated and model_def.last_updated > model_def.last_run:
            return True
        return False

    def process_model_definition(self, model_def):
        try:
            tool_name = f"{model_def.app_name}_{model_def.model_name}_tool"
            description = f"Generate JSON for {model_def.app_name} {model_def.model_name}"
            complete_tool_schema = self.generate_complete_tool_schema(model_def, tool_name, description)
            ai_tool, created = AITools.objects.update_or_create(
                name=tool_name,
                defaults={
                    'model_definition': model_def,
                    'description': description,
                    'json_schema': json.dumps(complete_tool_schema, indent=4)
                }
            )
            if created:
                logger.info(f"Created new AI Tool: {tool_name}")
            else:
                logger.info(f"Updated existing AI Tool: {tool_name}")
        except Exception as e:
            logger.error(f"Error processing model definition: {model_def.app_name}.{model_def.model_name}")
            logger.exception(e)
            raise

    def generate_complete_tool_schema(self, model_def, tool_name, description):
        try:
            input_schema = self.generate_input_schema(model_def.fields)
            complete_tool_schema = {
                "name": tool_name,
                "description": description,
                "input_schema": input_schema
            }
            return complete_tool_schema
        except Exception as e:
            logger.error(f"Error generating complete tool schema for model: {model_def.app_name}.{model_def.model_name}")
            logger.exception(e)
            raise

    def generate_input_schema(self, field_names):
        properties = {}
        required = []
        for field_name in field_names:
            if self.is_user_input_field(field_name):
                properties[field_name] = {
                    "type": "string",  # Adjust based on actual field types or use a mapping if needed
                    "description": f"{field_name} of the model"
                }
                required.append(field_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def is_user_input_field(self, field_name):
        # Exclude fields that are not for direct user input
        excluded_names = ['id', 'created_at', 'updated_at', 'created_by']
        return field_name not in excluded_names