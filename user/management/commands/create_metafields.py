import json
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from user.services.shopify_connection import ShopifyConnectionManager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Creates metafields from metafields.json file."

    def handle(self, *args, **options):
        json_file = settings.BASE_DIR / 'shopify_metafields.json'

        try:
            with open(json_file, 'r') as file:
                metafields_data = json.load(file)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {json_file}"))
            return
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR(f"Invalid JSON in file: {json_file}"))
            return

        with ShopifyConnectionManager() as shopify_connection:
            self.create_metafields(shopify_connection, metafields_data)

        self.stdout.write(self.style.SUCCESS('Finished creating metafields'))

    def create_metafields(self, shopify_connection, metafields_data):
        for owner_type, metafields in metafields_data.items():
            for metafield in metafields:
                if not self.metafield_exists(shopify_connection, owner_type, metafield['namespace'], metafield['key']):
                    self.create_metafield(shopify_connection, owner_type, metafield)
                else:
                    self.stdout.write(self.style.WARNING(f"Metafield {metafield['name']} for {owner_type} already exists. Skipping."))

    def metafield_exists(self, shopify_connection, owner_type, namespace, key):
        query = """
        query getMetafieldDefinition($ownerType: MetafieldOwnerType!, $namespace: String!, $key: String!) {
            metafieldDefinitions(ownerType: $ownerType, namespace: $namespace, key: $key, first: 1) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
        """
        variables = {"ownerType": owner_type, "namespace": namespace, "key": key}
        result = self.execute_graphql_query(shopify_connection, query, variables)
        if result and 'data' in result and 'metafieldDefinitions' in result['data']:
            return len(result['data']['metafieldDefinitions']['edges']) > 0
        return False

    def create_metafield(self, shopify_connection, owner_type, metafield):
        query = """
        mutation createMetafieldDefinition($definition: MetafieldDefinitionInput!) {
            metafieldDefinitionCreate(definition: $definition) {
                createdDefinition {
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
            "definition": {
                "name": metafield['name'],
                "namespace": metafield['namespace'],
                "key": metafield['key'],
                "type": metafield['type']['name'].lower(),
                "ownerType": owner_type
            }
        }

        if 'description' in metafield:
            variables['definition']['description'] = metafield['description']

        result = self.execute_graphql_query(shopify_connection, query, variables)
        if result and 'data' in result and 'metafieldDefinitionCreate' in result['data']:
            created = result['data']['metafieldDefinitionCreate']
            if created['userErrors']:
                self.stderr.write(self.style.ERROR(f"Error creating metafield {metafield['name']} for {owner_type}: {created['userErrors']}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Created metafield: {metafield['name']} for {owner_type}"))
        else:
            self.stderr.write(self.style.ERROR(f"Unexpected response or error for metafield: {metafield['name']} for {owner_type}"))

    def execute_graphql_query(self, shopify_connection, query, variables=None):
        try:
            result = shopify_connection.execute_graphql_query(query, variables)
            if result is None:
                self.stderr.write(self.style.ERROR("GraphQL query returned None. Check your Shopify connection."))
                return None
            if 'errors' in result:
                for error in result['errors']:
                    self.stderr.write(self.style.ERROR(f"GraphQL Error: {error['message']}"))
                return None
            return result
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred while executing GraphQL query: {str(e)}"))
            return None