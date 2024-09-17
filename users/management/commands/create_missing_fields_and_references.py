#create_missing_fields_and_references.py

import json
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from user.services.shopify_connection import ShopifyConnectionManager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Creates missing fields and references for existing metaobject schemas."

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
            self.process_metaobject_schemas(shopify_connection, schemas['metaobject_schemas'])
            self.process_metafields(shopify_connection, schemas['metafield_schemas'])

        self.stdout.write(self.style.SUCCESS('Finished processing missing fields and references'))

    def process_metaobject_schemas(self, shopify_connection, metaobject_schemas):
        for schema in metaobject_schemas:
            existing_schema = self.get_metaobject_schema(shopify_connection, schema['type'])
            if existing_schema:
                self.update_metaobject_schema(shopify_connection, existing_schema['id'], schema)
            else:
                self.create_metaobject_schema(shopify_connection, schema)

    def get_metaobject_schema(self, shopify_connection, schema_type):
        query = """
        query getMetaobjectDefinitions {
            metaobjectDefinitions(first: 250) {
                edges {
                    node {
                        id
                        type
                        name
                        fieldDefinitions {
                            name
                            key
                            type {
                                name
                            }
                            validations {
                                name
                                value
                            }
                        }
                    }
                }
            }
        }
        """
        result = self.execute_graphql_query(shopify_connection, query)
        if result and 'data' in result and 'metaobjectDefinitions' in result['data']:
            for edge in result['data']['metaobjectDefinitions']['edges']:
                if edge['node']['type'] == schema_type:
                    return edge['node']
        return None

    def create_metaobject_schema(self, shopify_connection, schema):
        query = """
        mutation createMetaobjectDefinition($definition: MetaobjectDefinitionInput!) {
            metaobjectDefinitionCreate(definition: $definition) {
                metaobjectDefinition {
                    id
                    name
                    fieldDefinitions {
                        name
                        key
                        type {
                            name
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
                        "type": field['type'].upper()
                    } for field in schema['fieldDefinitions']
                ]
            }
        }

        result = self.execute_graphql_query(shopify_connection, query, variables)
        if result and 'data' in result and 'metaobjectDefinitionCreate' in result['data']:
            created = result['data']['metaobjectDefinitionCreate']
            if created['userErrors']:
                self.stderr.write(self.style.ERROR(f"Error creating metaobject schema {schema['name']}: {created['userErrors']}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Created metaobject schema: {schema['name']}"))
        else:
            self.stderr.write(self.style.ERROR(f"Unexpected response or error for metaobject schema: {schema['name']}"))

    def update_metaobject_schema(self, shopify_connection, schema_id, schema):
        existing_schema = self.get_metaobject_schema(shopify_connection, schema['type'])
        existing_fields = {field['name'].lower(): field for field in existing_schema['fieldDefinitions']}
        
        new_fields = []
        updated_fields = []

        for field in schema['fieldDefinitions']:
            if field['name'].lower() not in existing_fields:
                new_fields.append(field)
            else:
                updated_fields.append(field)

        if not new_fields and not updated_fields:
            self.stdout.write(self.style.SUCCESS(f"No fields to add or update for {schema['name']}"))
            return

        for field in new_fields:
            created_field = self.create_field(shopify_connection, schema_id, field)
            if created_field:
                self.update_field_validations(shopify_connection, schema_id, field)

        for field in updated_fields:
            self.update_field_validations(shopify_connection, schema_id, field)

        if new_fields:
            self.stdout.write(self.style.SUCCESS(f"Added {len(new_fields)} new fields to {schema['name']}"))
        if updated_fields:
            self.stdout.write(self.style.SUCCESS(f"Updated {len(updated_fields)} existing fields in {schema['name']}"))
            
    def create_field(self, shopify_connection, schema_id, field):
        query = """
        mutation createMetaobjectField($id: ID!, $definition: MetaobjectDefinitionUpdateInput!) {
            metaobjectDefinitionUpdate(
                id: $id
                definition: $definition
            ) {
                metaobjectDefinition {
                    id
                    name
                    fieldDefinitions {
                        name
                        key
                        type {
                            name
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
        field_type = field['type'].lower()
        field_definition = {
            "name": field['name'],
            "key": field['name'].lower().replace(' ', '_'),
            "type": field_type
        }

        if 'metaobject_reference' in field_type:
            # Get the referenced_type from the field definition
            referenced_type = field.get('referenced_type', field_type.split('.')[-1])
            metaobject_definition_id = self.get_metaobject_definition_id(shopify_connection, referenced_type)
            
            if metaobject_definition_id:
                field_definition["validations"] = [
                    {
                        "name": "metaobject_definition_id",
                        "value": metaobject_definition_id
                    }
                ]
            else:
                self.stderr.write(self.style.ERROR(f"Could not find MetaobjectDefinition ID for type: {referenced_type}"))
                return None

        variables = {
            "id": schema_id,
            "definition": {
                "fieldDefinitions": {
                    "create": field_definition
                }
            }
        }

        self.stdout.write(f"Creating field: {field['name']}")
        self.stdout.write(f"Variables: {json.dumps(variables, indent=2)}")

        result = self.execute_graphql_query(shopify_connection, query, variables)
        if result and 'data' in result and 'metaobjectDefinitionUpdate' in result['data']:
            updated = result['data']['metaobjectDefinitionUpdate']
            if updated['userErrors']:
                self.stderr.write(self.style.ERROR(f"Error creating field {field['name']}: {updated['userErrors']}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Created field: {field['name']}"))
                return field['name'].lower().replace(' ', '_')
        else:
            self.stderr.write(self.style.ERROR(f"Unexpected response for field creation: {field['name']}"))
        return None

    def get_field_id(self, shopify_connection, schema_id, field_name):
        query = """
        query getMetaobjectDefinition($id: ID!) {
            metaobjectDefinition(id: $id) {
                fieldDefinitions {
                    name
                    key
                }
            }
        }
        """
        variables = {"id": schema_id}

        result = self.execute_graphql_query(shopify_connection, query, variables)
        if result and 'data' in result and 'metaobjectDefinition' in result['data']:
            fields = result['data']['metaobjectDefinition']['fieldDefinitions']
            for field in fields:
                if field['name'] == field_name:
                    return field['key']
        return None

    def update_field_validations(self, shopify_connection, schema_id, field):
        field_key = self.get_field_id(shopify_connection, schema_id, field['name'])
        if not field_key:
            self.stderr.write(self.style.ERROR(f"Could not find field key for {field['name']}"))
            return

        query = """
        mutation updateMetaobjectField($id: ID!, $definition: MetaobjectDefinitionUpdateInput!) {
            metaobjectDefinitionUpdate(
                id: $id
                definition: $definition
            ) {
                metaobjectDefinition {
                    id
                    name
                    fieldDefinitions {
                        name
                        key
                        type {
                            name
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
        
        update_data = {
            "key": field_key,
            "name": field['name'],
        }

        if 'metaobject_reference' in field['type'].lower():
            # Get the referenced_type from the field definition
            referenced_type = field.get('referenced_type', field['type'].split('.')[-1])
            metaobject_definition_id = self.get_metaobject_definition_id(shopify_connection, referenced_type)
            
            if metaobject_definition_id:
                update_data["validations"] = [
                    {
                        "name": "metaobject_definition_id",
                        "value": metaobject_definition_id
                    }
                ]

        variables = {
            "id": schema_id,
            "definition": {
                "fieldDefinitions": [
                    {
                        "update": update_data
                    }
                ]
            }
        }

        self.stdout.write(f"Updating field: {field['name']}")
        self.stdout.write(f"Variables: {json.dumps(variables, indent=2)}")

        result = self.execute_graphql_query(shopify_connection, query, variables)
        if result and 'data' in result and 'metaobjectDefinitionUpdate' in result['data']:
            updated = result['data']['metaobjectDefinitionUpdate']
            if updated['userErrors']:
                self.stderr.write(self.style.ERROR(f"Error updating field {field['name']}: {updated['userErrors']}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Updated field: {field['name']}"))
        else:
            self.stderr.write(self.style.ERROR(f"Unexpected response for field update: {field['name']}"))


    def create_single_metafield(self, shopify_connection, owner_type, metafield):
        query = """
        mutation createMetafieldDefinition($definition: MetafieldDefinitionInput!) {
            metafieldDefinitionCreate(definition: $definition) {
                createdDefinition {
                    id
                    name
                    namespace
                    key
                    type {
                        name
                    }
                    validations {
                        name
                        value
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """

        metafield_type = metafield['type']['name'].upper()
        if metafield_type.startswith('LIST.'):
            metafield_type = f"list.{metafield_type[5:].lower()}"  # Convert list types to lowercase
        elif metafield_type == 'METAOBJECT_REFERENCE':
            metafield_type = 'metaobject_reference'  # Use correct type name

        variables = {
            "definition": {
                "name": metafield['name'],
                "namespace": metafield['namespace'],
                "key": metafield['key'],
                "type": metafield_type,
                "ownerType": owner_type
            }
        }

        if 'description' in metafield:
            variables['definition']['description'] = metafield['description']

        if 'metaobject_reference' in metafield_type:
            referenced_type = metafield.get('referenced_type')
            if referenced_type:
                metaobject_definition_id = self.get_metaobject_definition_id(
                    shopify_connection, referenced_type
                )

                # Debug logging (optional, but helpful for troubleshooting)
                self.stdout.write(f"DEBUG: metafield_type: {metafield_type}")
                self.stdout.write(f"DEBUG: referenced_type: {referenced_type}")
                self.stdout.write(f"DEBUG: metaobject_definition_id: {metaobject_definition_id}")

                # ALWAYS add validations for metaobject_reference
                if metaobject_definition_id:  
                    variables['definition']['validations'] = [
                        {
                            "name": "metaobject_definition_id",
                            "value": metaobject_definition_id
                        }
                    ]
                else:
                    self.stderr.write(
                        self.style.ERROR(
                            f"Could not find MetaobjectDefinition ID for type: {referenced_type}"
                        )
                    )
                    return

        # Detailed Debug Logging
        self.stdout.write(f"DEBUG: GraphQL Variables:\n{json.dumps(variables, indent=2)}")

        result = self.execute_graphql_query(shopify_connection, query, variables)
        if result and 'data' in result and 'metafieldDefinitionCreate' in result['data']:
            created = result['data']['metafieldDefinitionCreate']
            if created['userErrors']:
                self.stderr.write(
                    self.style.ERROR(
                        f"Error creating metafield {metafield['name']} for {owner_type}: {created['userErrors']}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created metafield: {metafield['name']} for {owner_type}"
                    )
                )
        else:
            self.stderr.write(
                self.style.ERROR(
                    f"Unexpected response or error for metafield: {metafield['name']} for {owner_type}"
                )
            )

    def get_metaobject_definition_id(self, shopify_connection, metaobject_type):
        query = """
        query {
            metaobjectDefinitions(first: 250) {
                edges {
                    node {
                        id
                        type
                    }
                }
            }
        }
        """
        result = self.execute_graphql_query(shopify_connection, query)
        if result and 'data' in result and 'metaobjectDefinitions' in result['data']:
            for edge in result['data']['metaobjectDefinitions']['edges']:
                if edge['node']['type'].lower() == metaobject_type.lower():
                    return edge['node']['id']
        self.stderr.write(self.style.WARNING(f"Could not find MetaobjectDefinition ID for type: {metaobject_type}"))
        return None

    def process_metafields(self, shopify_connection, metafield_schemas):
        for owner_type, metafields in metafield_schemas.items():
            for metafield in metafields:
                existing_metafield = self.get_metafield_definition(shopify_connection, owner_type, metafield['namespace'], metafield['key'])
                if existing_metafield:
                    self.stdout.write(self.style.SUCCESS(f"Metafield {metafield['name']} for {owner_type} already exists. Skipping."))
                else:
                    self.create_single_metafield(shopify_connection, owner_type, metafield)

    def get_metafield_definition(self, shopify_connection, owner_type, namespace, key):
        query = """
        query getMetafieldDefinition($ownerType: MetafieldOwnerType!, $namespace: String!, $key: String!) {
            metafieldDefinitions(ownerType: $ownerType, namespace: $namespace, key: $key, first: 1) {
                edges {
                    node {
                        id
                        name
                        key
                        namespace
                    }
                }
            }
        }
        """
        variables = {"ownerType": owner_type, "namespace": namespace, "key": key}
        result = self.execute_graphql_query(shopify_connection, query, variables)
        if result and 'data' in result and 'metafieldDefinitions' in result['data']:
            edges = result['data']['metafieldDefinitions']['edges']
            if edges:
                return edges[0]['node']
        return None



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