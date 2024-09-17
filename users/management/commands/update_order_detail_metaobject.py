import json
import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from user.services.shopify_connection import ShopifyConnectionManager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update the order_detail Shopify metaobject definition'

    def handle(self, *args, **options):
        file_path = os.path.join(settings.BASE_DIR, 'meta_order.json')

        try:
            with open(file_path, 'r') as file:
                desired_field_definitions = json.load(file)['order_detail']

            self.update_order_detail_metaobject(desired_field_definitions)
        except Exception as e:
            logger.exception(f"Error in update_order_detail_metaobject command: {str(e)}")
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))

    def get_existing_field_definitions(self):
        query = """
        query {
          metaobjectDefinition(id: "gid://shopify/MetaobjectDefinition/order_detail") {
            id
            name
            fieldDefinitions {
              id
              key
              name
            }
          }
        }
        """
        with ShopifyConnectionManager() as shopify_connection:
            result = shopify_connection.execute_graphql_query(query)
            if 'data' in result and 'metaobjectDefinition' in result['data']:
                return result['data']['metaobjectDefinition']['fieldDefinitions']
            return []

    def update_order_detail_metaobject(self, desired_field_definitions):
        existing_field_definitions = self.get_existing_field_definitions()

        variables = {
            "id": "gid://shopify/MetaobjectDefinition/order_detail",
            "definition": {
                "fieldDefinitions": {}  # Initialize as an empty dictionary
            }
        }

        create_operations = []
        update_operations = []

        for desired_field in desired_field_definitions:
            existing_field = next((f for f in existing_field_definitions if f['key'] == desired_field['key']), None)
            field_def = {
                "key": desired_field['key'],
                "name": desired_field['name'],
                "type": desired_field['type'],
                "description": desired_field.get('description', ''),
                "validations": [
                    {
                        "name": validation['name'],
                        "value": json.dumps(validation['value'])
                    }
                    for validation in desired_field.get('validations', [])
                ]
            }

            if existing_field:
                field_def["id"] = existing_field['id']
                update_operations.append(field_def)
            else:
                create_operations.append(field_def)

        # Add create and update operations to variables only if they are not empty
        if create_operations:
            variables["definition"]["fieldDefinitions"]["create"] = create_operations
        if update_operations:
            variables["definition"]["fieldDefinitions"]["update"] = update_operations

        query = """
        mutation updateMetaobjectDefinition($id: ID!, $definition: MetaobjectDefinitionUpdateInput!) {
            metaobjectDefinitionUpdate(id: $id, definition: $definition) {
                metaobjectDefinition {
                    id
                    name
                    fieldDefinitions {
                        name
                        key
                        type {
                            name
                        }
                        description
                        validations {
                            name
                            value
                        }
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """

        with ShopifyConnectionManager() as shopify_connection:
            result = shopify_connection.execute_graphql_query(query, variables)
            logger.debug(f"Shopify API response: {result}")

        self.handle_update_result(result)

    def handle_update_result(self, result):
        if result is None:
            logger.error("No response received from Shopify API")
            raise Exception("No response received from Shopify API")

        if 'errors' in result:
            logger.error(f"GraphQL errors: {result['errors']}")
            raise Exception(f"GraphQL errors: {result['errors']}")

        if 'data' not in result:
            logger.error(f"Unexpected response structure: {result}")
            raise Exception("Unexpected response structure from Shopify API")

        update_result = result['data']['metaobjectDefinitionUpdate']
        if update_result.get('userErrors'):
            for error in update_result['userErrors']:
                logger.error(f"Error updating metaobject: {error['message']}")
                self.stderr.write(self.style.ERROR(f"Error: {error['message']}"))
        elif update_result.get('metaobjectDefinition'):
            logger.info('Successfully updated order_detail metaobject definition')
            self.stdout.write(self.style.SUCCESS('Successfully updated order_detail metaobject definition'))
        else:
            logger.error(f"Unexpected update result: {update_result}")
            raise Exception("Unexpected update result from Shopify API")