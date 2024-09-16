import json
from django.core.management.base import BaseCommand
from user.services.shopify_connection import ShopifyConnectionManager

class Command(BaseCommand):
    help = 'Update Shopify metaobject definitions with relationships'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default='metaobject_relationships.json', help='Path to the JSON file containing metaobject relationship updates')

    def handle(self, *args, **options):
        file_path = options['file']
        with open(file_path, 'r') as file:
            updates = json.load(file)

        for metaobject_name, fields in updates.items():
            self.update_metaobject_definition(metaobject_name, fields)

    def update_metaobject_definition(self, metaobject_name, fields):
        query = """
        mutation updateMetaobjectDefinition($id: ID!, $definition: MetaobjectDefinitionUpdateInput!) {
          metaobjectDefinitionUpdate(id: $id, definition: $definition) {
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
        
        variables = {
            "id": f"gid://shopify/MetaobjectDefinition/{metaobject_name}",
            "definition": {
                "fieldDefinitions": fields
            }
        }

        with ShopifyConnectionManager() as shopify_connection:
            result = shopify_connection.execute_graphql_query(query, variables)

        if result.get('data', {}).get('metaobjectDefinitionUpdate', {}).get('userErrors'):
            self.stdout.write(self.style.ERROR(f"Error updating {metaobject_name}: {result['data']['metaobjectDefinitionUpdate']['userErrors']}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully updated {metaobject_name}"))