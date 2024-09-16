from django.core.management.base import BaseCommand
from django.db import transaction
from user.models import Kiosk, Product, KioskQRCode
from user.services.shopify_connection import ShopifyConnectionManager
import logging
import json

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates products associated with a kiosk with their respective QR code lists'

    def add_arguments(self, parser):
        parser.add_argument('kiosk_id', type=str, help='The UUID of the Kiosk to update products for')

    @transaction.atomic
    def handle(self, *args, **options):
        kiosk_id = options['kiosk_id']

        try:
            kiosk = Kiosk.objects.get(id=kiosk_id)
        except Kiosk.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Kiosk with ID {kiosk_id} does not exist'))
            return

        self.stdout.write(self.style.SUCCESS(f'Updating products for kiosk: {kiosk.name} (ID: {kiosk.id})'))

        shopify_connection = ShopifyConnectionManager()

        try:
            products = kiosk.products.all()
            for product in products:
                self.update_product_qr_codes(shopify_connection, kiosk, product)

            self.stdout.write(self.style.SUCCESS('All products updated successfully'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred while updating products: {str(e)}'))
            logger.exception('Error in update_kiosk_product_qr_codes command')

    def update_product_qr_codes(self, shopify_connection, kiosk, product):
        qr_codes = KioskQRCode.objects.filter(kiosk=kiosk, product=product)
        self.stdout.write(f"Found {qr_codes.count()} QR codes for product {product.title}")
        
        qr_code_gids = [qr.shopify_id for qr in qr_codes if qr.shopify_id]
        self.stdout.write(f"QR code GIDs: {qr_code_gids}")

        if not qr_code_gids:
            self.stdout.write(self.style.WARNING(f'No valid QR codes found for product: {product.title}'))
            return

        mutation = """
        mutation productUpdate($input: ProductInput!) {
            productUpdate(input: $input) {
                product {
                    id
                    metafields(first: 10) {
                        edges {
                            node {
                                id
                                key
                                namespace
                                value
                            }
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
            "input": {
                "id": product.shopify_id,
                "metafields": [
                    {
                        "namespace": "custom",
                        "key": "kiosk_qr_codes",
                        "value": json.dumps(qr_code_gids),
                        "type": "list.metaobject_reference"
                    }
                ]
            }
        }

        self.stdout.write(f"Mutation variables: {json.dumps(variables, indent=2)}")

        result = shopify_connection.execute_graphql_query(mutation, variables)

        self.stdout.write(f"GraphQL result: {json.dumps(result, indent=2)}")

        if result and 'data' in result and 'productUpdate' in result['data']:
            if result['data']['productUpdate']['userErrors']:
                errors = result['data']['productUpdate']['userErrors']
                self.stdout.write(self.style.ERROR(f'Error updating product {product.title}: {errors}'))
            else:
                updated_metafields = result['data']['productUpdate']['product']['metafields']['edges']
                kiosk_qr_codes_metafield = next((m for m in updated_metafields if m['node']['key'] == 'kiosk_qr_codes'), None)
                if kiosk_qr_codes_metafield:
                    self.stdout.write(self.style.SUCCESS(f'Successfully updated QR codes for product: {product.title}'))
                    self.stdout.write(f'Updated value: {kiosk_qr_codes_metafield["node"]["value"]}')
                else:
                    self.stdout.write(self.style.WARNING(f'QR codes updated for product {product.title}, but metafield not found in response'))
        else:
            self.stdout.write(self.style.ERROR(f'Failed to update QR codes for product: {product.title}'))