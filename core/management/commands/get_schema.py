# yourapp/management/commands/get_schema.py

import json
import logging
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder
from core.supabase.schema_service import SchemaService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Retrieves the database schema and outputs it as JSON'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Specify an output file for the JSON (optional)',
        )

    def handle(self, *args, **options):
        schema_service = SchemaService()

        try:
            schema = schema_service.get_schema()
            json_schema = json.dumps(schema, cls=DjangoJSONEncoder, indent=2)

            if options['output']:
                with open(options['output'], 'w') as f:
                    f.write(json_schema)
                self.stdout.write(self.style.SUCCESS(f"Schema successfully written to {options['output']}"))
                logger.info(f"Schema successfully written to {options['output']}")
            else:
                self.stdout.write(json_schema)
                logger.info("Schema successfully retrieved and displayed")

        except Exception as e:
            error_message = f"An error occurred while retrieving the schema: {str(e)}"
            self.stderr.write(self.style.ERROR(error_message))
            logger.error(error_message, exc_info=True)