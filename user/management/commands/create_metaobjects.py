import json
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from user.services.shopify_connection import ShopifyConnectionManager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Creates basic metaobject schemas and metafields without complex references."

    def handle(self, *args, **options):
        json_file = settings.BASE_DIR / 'shopify_schemas.json'

        try:
            with open(json_file, 'r') as file:
                schemas = json.load(file)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {json_file}"))
            return
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR(f"Invalid JSON in file: {json_file}"))
            return

        with ShopifyConnectionManager() as shopify_connection:
            self.create_basic_metaobject_schemas(shopify_connection, schemas['metaobject_schemas'])
            self.create_basic_metafields(shopify_connection, schemas['metafield_schemas'])

        self.stdout.write(self.style.SUCCESS('Finished creating basic schemas and metafields'))

    def create_basic_metaobject_schemas(self, shopify_connection, metaobject_schemas):
        for schema in metaobject_schemas:
            if not self.metaobject_schema_exists(shopify_connection, schema['type']):
                self.create_metaobject_schema(shopify_connection, schema)

    def metaobject_schema_exists(self, shopify_connection, schema_type):
        query = """
        query getMetaobjectDefinitions {
            metaobjectDefinitions(first: 250) {
                edges {
                    node {
                        type
                    }
                }
            }
        }
        """
        result = self.execute_graphql_query(shopify_connection, query)
        if result and 'data' in result and 'metaobjectDefinitions' in result['data']:
            for edge in result['data']['metaobjectDefinitions']['edges']:
                if edge['node']['type'] == schema_type:
                    return True
        return False

    def create_metaobject_schema(self, shopify_connection, schema):
        query = """
        mutation createMetaobjectDefinition($definition: MetaobjectDefinitionCreateInput!) {
            metaobjectDefinitionCreate(definition: $definition) {
                metaobjectDefinition {
                    id
                    name
                    type
                    fieldDefinitions {
                        name
                        type {
                            name
                        }
                    }
                    access {
                        storefront
                    }
                    capabilities {
                        publishable {
                            enabled
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
        variables = {
            "definition": {
                "name": schema['name'],
                "type": schema['type'],
                "fieldDefinitions": [
                    {
                        "name": field['name'],
                        "key": field['name'].lower().replace(' ', '_'),
                        "type": field['type'].lower(),
                        "required": field.get('required', False),
                        "description": field.get('description', '')
                    } for field in schema['fieldDefinitions'] if not self.is_complex_field(field)
                ],
                "capabilities": {
                    "publishable": {
                        "enabled": schema.get('options', {}).get('active_draft_status', False)
                    }
                },
                "access": {
                    "storefront": "PUBLIC_READ" if schema.get('options', {}).get('storefronts_access', False) else "NONE"
                }
            }
        }

        self.stdout.write(self.style.WARNING(f"Sending variables to API: {json.dumps(variables, indent=2)}"))

        result = self.execute_graphql_query(shopify_connection, query, variables)
        if result and 'data' in result and 'metaobjectDefinitionCreate' in result['data']:
            created = result['data']['metaobjectDefinitionCreate']
            if created['userErrors']:
                self.stderr.write(self.style.ERROR(f"Error creating metaobject schema {schema['name']}: {created['userErrors']}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Created metaobject schema: {schema['name']}"))
                self.stdout.write(self.style.SUCCESS(f"Type: {created['metaobjectDefinition']['type']}"))
                self.stdout.write(self.style.SUCCESS(f"Field Definitions: {created['metaobjectDefinition']['fieldDefinitions']}"))
                self.stdout.write(self.style.SUCCESS(f"Access: {created['metaobjectDefinition']['access']}"))
                self.stdout.write(self.style.SUCCESS(f"Capabilities: {created['metaobjectDefinition']['capabilities']}"))
        else:
            self.stderr.write(self.style.ERROR(f"Unexpected response or error for metaobject schema: {schema['name']}"))
            self.stderr.write(self.style.ERROR(f"Full response: {json.dumps(result, indent=2)}"))
    
    
    def is_complex_field(self, field):
        return 'metaobject_reference' in field['type'].lower()

    def create_basic_metafields(self, shopify_connection, metafield_schemas):
        for owner_type, metafields in metafield_schemas.items():
            for metafield in metafields:
                if not self.is_complex_metafield(metafield):
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
    def is_complex_metafield(self, metafield):
        return 'metaobject_reference' in metafield['type']['name'].lower()

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