import logging
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from user.models import Kiosk, KioskQRCode, Product, Collection
from user.services.shopify_connection import ShopifyConnectionManager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Set up and update QR codes for a kiosk, update products with collections, and update related models'

    def add_arguments(self, parser):
        parser.add_argument('kiosk_id', type=str, help='The ID of the kiosk')

    def handle(self, *args, **options):
        kiosk_id = options['kiosk_id']
        
        try:
            kiosk = Kiosk.objects.get(id=kiosk_id)
        except Kiosk.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Kiosk with ID {kiosk_id} does not exist'))
            return

        self.stdout.write(f'Processing QR codes for kiosk: {kiosk.name} (ID: {kiosk.id})')

        with ShopifyConnectionManager() as manager:
            self.update_kiosk_collection(kiosk, manager)
            self.process_kiosk_qr_codes(kiosk, manager)
            self.update_products_with_qr_codes(kiosk, manager)

        self.stdout.write(self.style.SUCCESS(f'Finished processing QR codes for kiosk: {kiosk.name}'))

    def update_kiosk_collection(self, kiosk, manager):
        if not kiosk.collection:
            self.stdout.write(self.style.WARNING(f'Kiosk {kiosk.id} does not have an associated collection'))
            return

        query = """
        query getCollectionMetafields($id: ID!) {
            collection(id: $id) {
                metafields(first: 10) {
                    edges {
                        node {
                            id
                            namespace
                            key
                        }
                    }
                }
            }
        }
        """
        variables = {
            "id": self.get_shopify_gid(kiosk.collection.shopify_id, "Collection")
        }
        result = manager.execute_graphql_query(query, variables)
        
        existing_metafields = {}
        if result and 'data' in result and 'collection' in result['data']:
            for edge in result['data']['collection']['metafields']['edges']:
                node = edge['node']
                existing_metafields[f"{node['namespace']}.{node['key']}"] = node['id']

        metafields = [
            {
                "namespace": "custom",
                "key": "kiosk",
                "value": self.get_shopify_gid(kiosk.shopify_id, "Metaobject"),
                "type": "metaobject_reference",
                **({"id": existing_metafields["custom.kiosk"]} if "custom.kiosk" in existing_metafields else {})
            },
            {
                "namespace": "custom",
                "key": "kiosk_active",
                "value": "true",
                "type": "boolean",
                **({"id": existing_metafields["custom.kiosk_active"]} if "custom.kiosk_active" in existing_metafields else {})
            }
        ]

        mutation = """
        mutation collectionUpdate($input: CollectionInput!) {
            collectionUpdate(input: $input) {
                collection {
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
            "input": {
                "id": self.get_shopify_gid(kiosk.collection.shopify_id, "Collection"),
                "metafields": metafields
            }
        }

        result = manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'collectionUpdate' in result['data']:
            collection_update = result['data']['collectionUpdate']
            if not collection_update.get('userErrors'):
                self.stdout.write(self.style.SUCCESS(f'Updated collection {kiosk.collection.id} for kiosk {kiosk.id}'))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to update collection. Errors: {collection_update['userErrors']}"))
        else:
            self.stdout.write(self.style.ERROR(f'Failed to update collection for kiosk {kiosk.id}'))

    def process_kiosk_qr_codes(self, kiosk, manager):
        for kiosk_qr_code in kiosk.kiosk_qr_codes.all():
            self.update_kiosk_qr_code(kiosk_qr_code, manager)

    def update_kiosk_qr_code(self, kiosk_qr_code, manager):
        if not kiosk_qr_code.qr_code_url or not kiosk_qr_code.image_url:
            self.stdout.write(self.style.WARNING(f'Skipping QR code {kiosk_qr_code.id} due to missing URL or image'))
            return

        mutation = """
        mutation metaobjectUpdate($id: ID!, $metaobject: MetaobjectUpdateInput!) {
            metaobjectUpdate(id: $id, metaobject: $metaobject) {
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
            "id": self.get_shopify_gid(kiosk_qr_code.shopify_id, "Metaobject"),
            "metaobject": {
                "fields": [
                    {"key": "kiosk", "value": self.get_shopify_gid(kiosk_qr_code.kiosk.shopify_id, "Metaobject")},
                    {"key": "product", "value": self.get_shopify_gid(kiosk_qr_code.product.shopify_id, "Product")},
                    {"key": "qr_code_url", "value": kiosk_qr_code.qr_code_url},
                    {"key": "qr_code_image", "value": kiosk_qr_code.image_url}
                ]
            }
        }

        result = manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'metaobjectUpdate' in result['data']:
            self.stdout.write(self.style.SUCCESS(f'Updated QR code {kiosk_qr_code.id} in Shopify'))
        else:
            self.stdout.write(self.style.ERROR(f'Failed to update QR code {kiosk_qr_code.id} in Shopify'))

    def update_products_with_qr_codes(self, kiosk, manager):
        for product in kiosk.products.all():
            self.update_product_metafields(product, kiosk, manager)

    def update_product_metafields(self, product, kiosk, manager):
        query = """
        query getProductMetafields($id: ID!) {
            product(id: $id) {
                metafields(first: 10) {
                    edges {
                        node {
                            id
                            namespace
                            key
                        }
                    }
                }
            }
        }
        """
        variables = {
            "id": self.get_shopify_gid(product.shopify_id, "Product")
        }
        result = manager.execute_graphql_query(query, variables)
        
        existing_metafields = {}
        if result and 'data' in result and 'product' in result['data']:
            for edge in result['data']['product']['metafields']['edges']:
                node = edge['node']
                existing_metafields[f"{node['namespace']}.{node['key']}"] = node['id']

        qr_codes = KioskQRCode.objects.filter(kiosk=kiosk, product=product)
        qr_code_ids = [self.get_shopify_gid(qr_code.shopify_id, "Metaobject") for qr_code in qr_codes]
        
        collections = product.kiosk_collections.filter(kiosk=kiosk)
        collection_ids = [self.get_shopify_gid(collection.shopify_id, "Collection") for collection in collections]

        metafields = [
            {
                "namespace": "custom",
                "key": "kiosk_qr_codes",
                "value": json.dumps(qr_code_ids),
                "type": "list.metaobject_reference",
                **({"id": existing_metafields["custom.kiosk_qr_codes"]} if "custom.kiosk_qr_codes" in existing_metafields else {})
            },
            {
                "namespace": "custom",
                "key": "kiosk_collections",
                "value": json.dumps(collection_ids),
                "type": "list.collection_reference",
                **({"id": existing_metafields["custom.kiosk_collections"]} if "custom.kiosk_collections" in existing_metafields else {})
            },
            {
                "namespace": "custom",
                "key": "kiosk_active",
                "value": str(product.is_kiosk_active).lower(),
                "type": "boolean",
                **({"id": existing_metafields["custom.kiosk_active"]} if "custom.kiosk_active" in existing_metafields else {})
            }
        ]

        mutation = """
        mutation productUpdate($input: ProductInput!) {
            productUpdate(input: $input) {
                product {
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
            "input": {
                "id": self.get_shopify_gid(product.shopify_id, "Product"),
                "metafields": metafields
            }
        }

        result = manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'productUpdate' in result['data']:
            product_update = result['data']['productUpdate']
            if not product_update.get('userErrors'):
                self.stdout.write(self.style.SUCCESS(f'Updated product {product.id} with QR codes and collections'))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to update product {product.id}. Errors: {product_update['userErrors']}"))
        else:
            self.stdout.write(self.style.ERROR(f'Failed to update product {product.id} with QR codes and collections'))

    def get_shopify_gid(self, id_value, resource_type):
        if isinstance(id_value, str) and id_value.startswith('gid://shopify/'):
            return id_value
        return f'gid://shopify/{resource_type}/{id_value}'