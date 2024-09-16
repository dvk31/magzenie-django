import json
import logging
from django.core.management.base import BaseCommand
from user.services.shopify_connection import ShopifyConnectionManager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create a specific Shopify metaobject definition'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Full path to the JSON file containing order_detail metaobject definition')
        parser.add_argument('--object', type=str, required=True, help='Name of the metaobject to create')

    def handle(self, *args, **options):
        file_path = options['file']

        try:
            with open(file_path, 'r') as file:
                file_contents = file.read()
                try:
                    order_detail_def = json.loads(file_contents)
                except json.JSONDecodeError as json_error:
                    logger.error(f"JSON Decode Error: {str(json_error)}")
                    logger.error(f"File contents: {file_contents}")
                    raise
            
            self.update_order_detail_metaobject(order_detail_def)
        except Exception as e:
            logger.exception(f"Error in update_order_detail_metaobject command: {str(e)}")
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))


    def load_metaobject_definition(self, file_path, object_name):
        try:
            with open(file_path, 'r') as file:
                definitions = json.load(file)
        except FileNotFoundError:
            logger.error(f'File not found: {file_path}')
            raise FileNotFoundError(f'File not found: {file_path}')
        except json.JSONDecodeError:
            logger.error(f'Invalid JSON in file: {file_path}')
            raise ValueError(f'Invalid JSON in file: {file_path}')

        metaobject_def = next((obj for obj in definitions['metaobjects'] if obj['name'] == object_name), None)

        if not metaobject_def:
            logger.error(f'Metaobject "{object_name}" not found in the definitions file')
            raise ValueError(f'Metaobject "{object_name}" not found in the definitions file')

        return metaobject_def

    def create_metaobject_definition(self, metaobject_def):
        query = self.get_create_metaobject_query()
        variables = self.prepare_metaobject_variables(metaobject_def)

        with ShopifyConnectionManager() as shopify_connection:
            result = shopify_connection.execute_graphql_query(query, variables)
            logger.debug(f"Shopify API response: {result}")

        self.handle_creation_result(result, metaobject_def['name'])

    def get_create_metaobject_query(self):
        return """
        mutation createMetaobjectDefinition($definition: MetaobjectDefinitionCreateInput!) {
          metaobjectDefinitionCreate(definition: $definition) {
            metaobjectDefinition {
              id
              name
            }
            userErrors {
              field
              message
            }
          }
        }
        """

    def prepare_metaobject_variables(self, metaobject_def):
        variables = {
            "definition": {
                "name": metaobject_def['name'],
                "type": metaobject_def['name'].upper(),
                "fieldDefinitions": [
                    {
                        "name": field['name'],
                        "key": field['key'],
                        "type": field['type']  # Change this line
                    } for field in metaobject_def['fields']
                ]
            }
        }
        logger.debug(f"Prepared variables: {variables}")
        return variables

    def handle_creation_result(self, result, object_name):
        if result is None:
            logger.error("No response received from Shopify API")
            raise Exception("No response received from Shopify API")

        if 'errors' in result:
            logger.error(f"GraphQL errors: {result['errors']}")
            raise Exception(f"GraphQL errors: {result['errors']}")

        if 'data' not in result:
            logger.error(f"Unexpected response structure: {result}")
            raise Exception("Unexpected response structure from Shopify API")

        creation_result = result['data']['metaobjectDefinitionCreate']
        if creation_result.get('userErrors'):
            for error in creation_result['userErrors']:
                logger.error(f"Error creating metaobject: {error['message']}")
                self.stderr.write(self.style.ERROR(f"Error: {error['message']}"))
        elif creation_result.get('metaobjectDefinition'):
            logger.info(f'Successfully created metaobject definition: {object_name}')
            self.stdout.write(self.style.SUCCESS(f'Successfully created metaobject definition: {object_name}'))
        else:
            logger.error(f"Unexpected creation result: {creation_result}")
            raise Exception("Unexpected creation result from Shopify API")