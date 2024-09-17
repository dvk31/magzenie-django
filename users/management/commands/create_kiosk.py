# user/management/commands/create_kiosks.py

import json
import logging
import traceback
from django.core.management.base import BaseCommand
from user.models import PartnerStore, Kiosk, Product, KioskQRCode
from user.services.shopify_connection import ShopifyConnectionManager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create kiosks in Shopify and update Django models'

    def add_arguments(self, parser):
        parser.add_argument('store_id', type=str, help='The ID of the store to process')

    def handle(self, *args, **options):
        store_id = options['store_id']
        try:
            store = PartnerStore.objects.get(id=store_id)
            logger.info(f"Processing kiosk creation for store: {store.name} (ID: {store.id})")

            products = self.load_products_from_json()
            
            with ShopifyConnectionManager() as manager:
                kiosk = self.create_kiosk_in_shopify(store, manager)
                if kiosk:
                    self.associate_products_with_kiosk(kiosk, products, manager)
                    self.stdout.write(self.style.SUCCESS(f'Kiosk created successfully for store {store.name}'))
                else:
                    self.stdout.write(self.style.ERROR(f'Failed to create kiosk for store {store.name}'))

        except PartnerStore.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Store with ID {store_id} does not exist'))
        except Exception as e:
            logger.critical(f"Critical error in handle method: {str(e)}")
            logger.debug(traceback.format_exc())
            self.stdout.write(self.style.ERROR('An error occurred during the kiosk creation process'))

    def load_products_from_json(self):
        try:
            with open('shopify_products.json', 'r') as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Error loading products from JSON: {str(e)}")
            return []

    def create_kiosk_in_shopify(self, store, manager):
        try:
            # First, fetch the metaobject definition to get the correct field names
            query = """
            query {
            metaobjectDefinitions(first: 10) {
                edges {
                node {
                    type
                    fieldDefinitions {
                    name
                    key
                    type {
                        name
                    }
                    }
                }
                }
            }
            }
            """
            
            result = manager.execute_graphql_query(query)
            
            if result is None or 'data' not in result or 'metaobjectDefinitions' not in result['data']:
                logger.error(f"Failed to fetch metaobject definitions: {result}")
                return None
            
            kiosk_definition = next((node['node'] for node in result['data']['metaobjectDefinitions']['edges'] if node['node']['type'].lower() == 'kiosk'), None)
            
            if not kiosk_definition:
                logger.error("KIOSK metaobject definition not found")
                return None
            
            field_keys = {fd['name'].lower(): {'key': fd['key'], 'type': fd['type']['name']} for fd in kiosk_definition['fieldDefinitions']}
            
            # Now create the kiosk using the correct field keys
            mutation = """
            mutation createKiosk($metaobject: MetaobjectCreateInput!) {
                metaobjectCreate(metaobject: $metaobject) {
                    metaobject {
                        id
                        handle
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """
            
            fields = []
            
            if 'name' in field_keys:
                fields.append({"key": field_keys['name']['key'], "value": f"Kiosk for {store.name}"})
            
            if 'store' in field_keys:
                if field_keys['store']['type'] == 'metaobject_reference':
                    fields.append({"key": field_keys['store']['key'], "value": store.shopify_id})
                else:
                    logger.warning(f"Store field is not a metaobject reference. Type: {field_keys['store']['type']}")
            
            if 'is_active' in field_keys:
                fields.append({"key": field_keys['is_active']['key'], "value": "true"})
            
            # Add optional fields if they exist
            optional_fields = ['kiosk_qr_code_url', 'products', 'qr codes', 'collection']
            for field in optional_fields:
                if field in field_keys:
                    if field_keys[field]['type'] in ['list.product_reference', 'list.metaobject_reference']:
                        fields.append({"key": field_keys[field]['key'], "value": "[]"})
                    else:
                        fields.append({"key": field_keys[field]['key'], "value": ""})
            
            variables = {
                "metaobject": {
                    "type": "kiosk",
                    "fields": fields
                }
            }

            logger.info(f"Sending GraphQL mutation to create kiosk for store: {store.name}")
            result = manager.execute_graphql_query(mutation, variables)
            logger.info(f"Received response from Shopify: {result}")

            if result is None or 'data' not in result or 'metaobjectCreate' not in result['data']:
                logger.error(f"Unexpected response structure from Shopify: {result}")
                return None

            metaobject_create = result['data']['metaobjectCreate']

            if metaobject_create['metaobject']:
                shopify_kiosk_id = metaobject_create['metaobject']['id']
                kiosk = Kiosk.objects.create(
                    shopify_id=shopify_kiosk_id,
                    name=f"Kiosk for {store.name}",
                    store=store,
                    is_active=True
                )
                logger.info(f"Created kiosk in Shopify and Django: {kiosk.name} (ID: {kiosk.id})")
                return kiosk
            else:
                errors = metaobject_create.get('userErrors', [])
                logger.error(f"Failed to create kiosk in Shopify: {errors}")
                return None

        except Exception as e:
            logger.error(f"Error creating kiosk in Shopify: {str(e)}")
            logger.debug(traceback.format_exc())
        return None

    def associate_products_with_kiosk(self, kiosk, products, manager):
        try:
            product_ids = []
            for product_data in products:
                shopify_product_id = product_data['shopify_id']
                
                # Fetch additional product details from Shopify if needed
                shopify_product = self.fetch_product_details_from_shopify(shopify_product_id, manager)
                
                if shopify_product:
                    product, created = Product.objects.update_or_create(
                        shopify_id=shopify_product_id,
                        defaults={
                            'title': shopify_product.get('title', ''),
                            'price': shopify_product.get('price', 0.00),
                            'description': shopify_product.get('description', ''),
                        }
                    )
                    kiosk.products.add(product)
                    product_ids.append(shopify_product_id)
                    
                    # Generate QR code URL
                    qr_code_url = self.generate_qr_code_url(kiosk, product)
                    
                    # Only create KioskQRCode if URL is not empty
                    if qr_code_url:
                        KioskQRCode.objects.update_or_create(
                            kiosk=kiosk,
                            product=product,
                            defaults={'qr_code_url': qr_code_url}
                        )
                else:
                    logger.warning(f"Failed to fetch details for product {shopify_product_id}")
            
            self.update_kiosk_products_in_shopify(kiosk, product_ids, manager)
            
            logger.info(f"Associated {len(product_ids)} products with kiosk {kiosk.name}")
        except Exception as e:
            logger.error(f"Error associating products with kiosk: {str(e)}")
            logger.debug(traceback.format_exc())

    def generate_qr_code_url(self, kiosk, product):
        # Implement your QR code URL generation logic here
        # This is a placeholder implementation
        return f"https://yourdomain.com/kiosk/{kiosk.id}/product/{product.id}"

    def update_kiosk_products_in_shopify(self, kiosk, product_ids, manager):
        try:
            mutation = """
            mutation updateKiosk($id: ID!, $fields: [MetaobjectFieldInput!]!) {
                metaobjectUpdate(id: $id, fields: $fields) {
                    metaobject {
                        id
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """
            
            variables = {
                "id": kiosk.shopify_id,
                "fields": [
                    {
                        "key": "Products",
                        "value": json.dumps(product_ids)
                    }
                ]
            }
            
            result = manager.execute_graphql_query(mutation, variables)
            
            if result and 'data' in result and 'metaobjectUpdate' in result['data']:
                if 'metaobject' in result['data']['metaobjectUpdate']:
                    logger.info(f"Updated kiosk {kiosk.name} in Shopify with {len(product_ids)} products")
                else:
                    errors = result['data']['metaobjectUpdate'].get('userErrors', [])
                    logger.error(f"Failed to update kiosk in Shopify: {errors}")
            else:
                logger.error(f"Unexpected response from Shopify: {result}")

        except Exception as e:
            logger.error(f"Error updating kiosk products in Shopify: {str(e)}")
            logger.debug(traceback.format_exc())

    def fetch_product_details_from_shopify(self, product_id, manager):
        query = """
        query getProduct($id: ID!) {
        product(id: $id) {
            title
            priceRange {
            minVariantPrice {
                amount
            }
            }
            description
            images(first: 1) {
            edges {
                node {
                src
                }
            }
            }
        }
        }
        """
        variables = {"id": product_id}
        
        result = manager.execute_graphql_query(query, variables)
        
        if result and 'data' in result and 'product' in result['data']:
            product = result['data']['product']
            return {
                'title': product['title'],
                'price': float(product['priceRange']['minVariantPrice']['amount']),
                'description': product['description'],
                'image': product['images']['edges'][0]['node']['src'] if product['images']['edges'] else None
            }
        else:
            logger.error(f"Failed to fetch product details from Shopify: {result}")
            return None

    def update_kiosk_products_in_shopify(self, kiosk, product_ids, manager):
        try:
            # First, fetch the metaobject definition to get the correct field key for products
            query = """
            query {
            metaobjectDefinitions(first: 10) {
                edges {
                node {
                    type
                    fieldDefinitions {
                    name
                    key
                    type {
                        name
                    }
                    }
                }
                }
            }
            }
            """
            
            result = manager.execute_graphql_query(query)
            
            if result is None or 'data' not in result or 'metaobjectDefinitions' not in result['data']:
                logger.error(f"Failed to fetch metaobject definitions: {result}")
                return
            
            kiosk_definition = next((node['node'] for node in result['data']['metaobjectDefinitions']['edges'] if node['node']['type'].lower() == 'kiosk'), None)
            
            if not kiosk_definition:
                logger.error("KIOSK metaobject definition not found")
                return
            
            field_keys = {fd['name'].lower(): {'key': fd['key'], 'type': fd['type']['name']} for fd in kiosk_definition['fieldDefinitions']}
            
            if 'products' not in field_keys:
                logger.error("Products field not found in KIOSK metaobject definition")
                return
            
            products_field_key = field_keys['products']['key']
            
            mutation = """
            mutation updateKiosk($id: ID!, $input: MetaobjectUpdateInput!) {
            metaobjectUpdate(id: $id, metaobject: $input) {
                metaobject {
                id
                }
                userErrors {
                field
                message
                }
            }
            }
            """
            
            variables = {
                "id": kiosk.shopify_id,
                "input": {
                    "fields": [
                        {
                            "key": products_field_key,
                            "value": json.dumps(product_ids)
                        }
                    ]
                }
            }
            
            result = manager.execute_graphql_query(mutation, variables)
            
            if result and 'data' in result and 'metaobjectUpdate' in result['data']:
                if 'metaobject' in result['data']['metaobjectUpdate']:
                    logger.info(f"Updated kiosk {kiosk.name} in Shopify with {len(product_ids)} products")
                else:
                    errors = result['data']['metaobjectUpdate'].get('userErrors', [])
                    logger.error(f"Failed to update kiosk in Shopify: {errors}")
            else:
                logger.error(f"Unexpected response from Shopify: {result}")

        except Exception as e:
            logger.error(f"Error updating kiosk products in Shopify: {str(e)}")
            logger.debug(traceback.format_exc())