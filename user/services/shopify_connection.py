#user/services/shopify_connection.py
import logging
from django.conf import settings
import shopify
from shopify.session import ValidationException
import requests
import re

logger = logging.getLogger(__name__)

class ShopifyConnectionManager:
    def __init__(self):
        self.admin_session = None
        self.admin_url = f"https://{settings.SHOPIFY_STORE_URL}/admin/api/{settings.SHOPIFY_API_VERSION}/graphql.json"
        self.admin_headers = {
            "X-Shopify-Access-Token": settings.SHOPIFY_ADMIN_ACCESS_TOKEN,
            "Content-Type": "application/json",
        }

    def __enter__(self):
        self.initialize_admin_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_admin_session()

    def initialize_admin_session(self):
        try:
            self.admin_session = shopify.Session(
                settings.SHOPIFY_STORE_URL,
                settings.SHOPIFY_API_VERSION,
                settings.SHOPIFY_ADMIN_ACCESS_TOKEN
            )
            shopify.ShopifyResource.activate_session(self.admin_session)
            logger.info("Shopify admin session initialized successfully")
        except ValidationException as e:
            logger.error(f"Failed to initialize Shopify admin session: {str(e)}")
            raise

    def close_admin_session(self):
        if self.admin_session:
            shopify.ShopifyResource.clear_session()
            logger.info("Shopify admin session closed")

    def execute_graphql_query(self, query, variables=None):
        payload = {"query": query, "variables": variables or {}}
        response = requests.post(self.admin_url, json=payload, headers=self.admin_headers)
        if response.status_code == 200:
            result = response.json()
            if 'errors' in result:
                logger.error(f"GraphQL query returned errors: {result['errors']}")
                return None
            return result
        else:
            logger.error(f"GraphQL query failed: {response.status_code} - {response.text}")
            return None

    def get_shop_info(self):
        query = """
        {
        shop {
            name
            email
            primaryDomain {
            url
            }
            currencyCode
        }
        }
        """
        result = self.execute_graphql_query(query)
        if result and 'data' in result and 'shop' in result['data']:
            shop_data = result['data']['shop']
            return {
                'name': shop_data['name'],
                'email': shop_data['email'],
                'domain': shop_data['primaryDomain']['url'],
                'currency': shop_data['currencyCode'],
                'country_name': '',  # You might need to fetch this separately
            }
        return None

        
    def get_product_info(self, product_id):
        # If the product_id is already in the correct format, use it as is
        if product_id.startswith('gid://shopify/Product/'):
            gid = product_id
        else:
            # If it's just the numeric ID, convert it to the full GID format
            gid = f"gid://shopify/Product/{product_id}"

        query = """
        query getProduct($id: ID!) {
        product(id: $id) {
            id
            title
            vendor
            productType
            tags
            variants(first: 250) {
            edges {
                node {
                id
                title
                price
                sku
                }
            }
            }
        }
        }
        """
        variables = {"id": gid}
        result = self.execute_graphql_query(query, variables)
        if result and 'data' in result and 'product' in result['data']:
            product_data = result['data']['product']
            
            # Extract the numeric ID from the full GID
            numeric_id = re.search(r'/Product/(\d+)', product_data['id']).group(1)
            
            return {
                'id': numeric_id,
                'title': product_data['title'],
                'vendor': product_data['vendor'],
                'product_type': product_data['productType'],
                'tags': product_data['tags'],
                'variants': [
                    {
                        'id': re.search(r'/ProductVariant/(\d+)', variant['node']['id']).group(1),
                        'title': variant['node']['title'],
                        'price': variant['node']['price'],
                        'sku': variant['node']['sku'],
                    } for variant in product_data['variants']['edges']
                ],
            }
        return None