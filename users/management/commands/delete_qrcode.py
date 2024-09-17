import logging
from django.core.management.base import BaseCommand
from user.services.shopify_connection import ShopifyConnectionManager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Delete "qr_code" metafield from all Shopify products'

    def handle(self, *args, **options):
        # GraphQL query to fetch products and their metafields
        query = """
        query {
          products(first: 100) {
            edges {
              node {
                id
                metafields(first: 10) {
                  edges {
                    node {
                      id
                      key
                      namespace
                    }
                  }
                }
              }
            }
          }
        }
        """

        with ShopifyConnectionManager() as manager:
            result = manager.execute_graphql_query(query)

        for edge in result['data']['products']['edges']:
            product_data = edge['node']
            metafields = product_data['metafields']['edges']

            for metafield in metafields:
                meta_node = metafield['node']
                if meta_node['key'] == 'qr_code':
                    # Mutation to delete the metafield
                    delete_mutation = """
                    mutation {
                      metafieldDelete(input: {id: "%s"}) {
                        deletedId
                        userErrors {
                          field
                          message
                        }
                      }
                    }
                    """ % meta_node['id']

                    delete_result = manager.execute_graphql_query(delete_mutation)

                    if 'userErrors' in delete_result['data']['metafieldDelete']:
                        errors = delete_result['data']['metafieldDelete']['userErrors']
                        for error in errors:
                            logger.error(f"Error deleting metafield: {error['message']}")
                    else:
                        self.stdout.write(self.style.SUCCESS(f"Deleted qr_code metafield for product {product_data['id']}"))

        self.stdout.write(self.style.SUCCESS("Completed deleting qr_code metafields"))