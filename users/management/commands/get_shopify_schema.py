import json
import logging
from django.core.management.base import BaseCommand
from user.services.shopify_connection import ShopifyConnectionManager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch Shopify metaobject and metafield schemas and save to a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default='shopify_schemas_output.json',
                            help='Output JSON file name')

    def handle(self, *args, **options):
        output_file = options['output']
        
        with ShopifyConnectionManager() as manager:
            metaobject_schemas = self.fetch_all_metaobject_schemas(manager)
            metafield_schemas = self.fetch_all_metafield_schemas(manager)
            resource_metafields = self.fetch_resource_metafields(manager)

        schemas = {
            "metaobject_schemas": metaobject_schemas,
            "metafield_schemas": metafield_schemas,
            "resource_metafields": resource_metafields
        }

        with open(output_file, 'w') as f:
            json.dump(schemas, f, indent=2)

        self.stdout.write(self.style.SUCCESS(f'Schemas successfully written to {output_file}'))

    def fetch_all_metaobject_schemas(self, manager):
        schemas = []
        has_next_page = True
        cursor = None

        while has_next_page:
            query = self.get_metaobject_query(cursor)
            result = manager.execute_graphql_query(query)

            if result and 'data' in result and 'metaobjectDefinitions' in result['data']:
                page_info = result['data']['metaobjectDefinitions']['pageInfo']
                has_next_page = page_info['hasNextPage']
                cursor = page_info['endCursor'] if has_next_page else None

                for edge in result['data']['metaobjectDefinitions']['edges']:
                    schemas.append(edge['node'])
            else:
                has_next_page = False
                logger.error(f"Failed to fetch metaobject schemas. Result: {result}")

        return schemas

    def fetch_all_metafield_schemas(self, manager):
        schemas = {}
        owner_types = ['CUSTOMER', 'PRODUCT', 'SHOP', 'COLLECTION', 'ORDER']

        for owner_type in owner_types:
            query = self.get_metafield_definitions_query(owner_type)
            result = manager.execute_graphql_query(query)

            if result and 'data' in result and 'metafieldDefinitions' in result['data']:
                schemas[owner_type] = [edge['node'] for edge in result['data']['metafieldDefinitions']['edges']]
            else:
                logger.error(f"Failed to fetch metafield schemas for {owner_type}. Result: {result}")
                self.stdout.write(self.style.WARNING(f'Failed to fetch metafield schemas for {owner_type}. Check permissions.'))

        return schemas

    def fetch_resource_metafields(self, manager):
        resource_types = ['CUSTOMER', 'PRODUCT', 'SHOP', 'COLLECTION', 'ORDER']
        resource_metafields = {}

        for resource_type in resource_types:
            query = self.get_resource_metafields_query(resource_type)
            result = manager.execute_graphql_query(query)

            if result and 'data' in result:
                if resource_type == 'SHOP':
                    resource_metafields[resource_type] = result['data']['shop']['metafields']['edges']
                elif resource_type in ['CUSTOMER', 'PRODUCT', 'COLLECTION', 'ORDER']:
                    nodes = result['data'].get(resource_type.lower(), {}).get('edges', [])
                    if nodes:
                        resource_metafields[resource_type] = nodes[0]['node']['metafields']['edges']
                    else:
                        logger.warning(f"No {resource_type} data found")
                        resource_metafields[resource_type] = []
            else:
                logger.error(f"Failed to fetch metafields for {resource_type}. Result: {result}")
                self.stdout.write(self.style.WARNING(f'Failed to fetch metafields for {resource_type}'))

        return resource_metafields

    def get_metaobject_query(self, cursor=None):
        return f"""
        query {{
          metaobjectDefinitions(first: 50, after: {json.dumps(cursor) if cursor else "null"}) {{
            pageInfo {{
              hasNextPage
              endCursor
            }}
            edges {{
              node {{
                name
                type
                fieldDefinitions {{
                  name
                  type {{
                    name
                  }}
                }}
              }}
            }}
          }}
        }}
        """

    def get_metafield_definitions_query(self, owner_type):
        return f"""
        query {{
          metafieldDefinitions(first: 50, ownerType: {owner_type}) {{
            edges {{
              node {{
                name
                key
                namespace
                type {{
                  name
                }}
                ownerType
              }}
            }}
          }}
        }}
        """

    def get_resource_metafields_query(self, resource_type):
        if resource_type == 'SHOP':
            return """
            query {
              shop {
                metafields(first: 50) {
                  edges {
                    node {
                      namespace
                      key
                      type
                      ownerType
                    }
                  }
                }
              }
            }
            """
        elif resource_type in ['CUSTOMER', 'PRODUCT', 'COLLECTION', 'ORDER']:
            return f"""
            query {{
              {resource_type.lower()}s(first: 1) {{
                edges {{
                  node {{
                    metafields(first: 50) {{
                      edges {{
                        node {{
                          namespace
                          key
                          type
                          ownerType
                        }}
                      }}
                    }}
                  }}
                }}
              }}
            }}
            """