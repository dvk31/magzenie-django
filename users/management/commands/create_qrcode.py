# management/commands/create_qrcode.py

import json
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from user.models import Kiosk, Product, KioskQRCode
from user.services.qr_code_service import QRCodeService
from user.services.shopify_connection import ShopifyConnectionManager
from django.conf import settings
from user.services.get_content_url import get_qr_code_image_url
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generates QR codes for products associated with a specific kiosk'

    def add_arguments(self, parser):
        parser.add_argument('kiosk_id', type=str, help='The ID of the kiosk to process')

    def handle(self, *args, **options):
        kiosk_id = options['kiosk_id']
        shopify_manager = ShopifyConnectionManager()

        try:
            kiosk = Kiosk.objects.get(id=kiosk_id)
        except Kiosk.DoesNotExist:
            raise CommandError(f'Kiosk with ID "{kiosk_id}" does not exist')

        self.stdout.write(f"Processing kiosk: {kiosk.name} (ID: {kiosk.id})")
        logger.info(f"Starting to process kiosk: {kiosk.name} (ID: {kiosk.id})")
        self.process_kiosk(kiosk, shopify_manager)
        self.stdout.write(self.style.SUCCESS("QR code generation completed successfully!"))
        logger.info("QR code generation completed successfully!")

    def process_kiosk(self, kiosk, shopify_manager):
        qr_service = QRCodeService(kiosk.id)
        product_qr_codes = []

        products = kiosk.products.all()
        logger.info(f"Found {products.count()} products for kiosk {kiosk.id}")

        for product in products:
            logger.info(f"Processing product: {product.id} for kiosk {kiosk.id}")
            try:
                qr_code_url, file_id, relative_url = qr_service.generate_and_upload_qr_code(str(product.id))
                
                if qr_code_url and file_id and relative_url:
                    full_url = f"{settings.PEEQSHOP_DOMAIN}/{relative_url}"
                    metaobject_id = self.create_qr_code_metaobject(shopify_manager, kiosk, product, full_url, file_id)
                    if metaobject_id:
                        product_qr_codes.append(metaobject_id)
                        self.update_product_metafields(shopify_manager, product, [metaobject_id])
                        logger.info(f"Successfully created and uploaded QR code for product {product.id} in kiosk {kiosk.id}")
                    else:
                        logger.warning(f"Failed to create metaobject for product {product.id} in kiosk {kiosk.id}")
                else:
                    logger.warning(f"Failed to generate QR code for product {product.id} in kiosk {kiosk.id}")
            except Exception as e:
                logger.error(f"Error processing product {product.id} for kiosk {kiosk.id}: {str(e)}", exc_info=True)

        logger.info(f"Finished processing all products. Total QR codes generated: {len(product_qr_codes)}")

        # Update kiosk metaobject with all QR codes
        self.update_kiosk_metaobject(shopify_manager, kiosk, product_qr_codes)

    def create_qr_code_metaobject(self, shopify_manager, kiosk, product, qr_code_url, file_id):
        logger.info(f"Creating QR code metaobject for product {product.id} in kiosk {kiosk.id}")
        image_url = get_qr_code_image_url(kiosk.id, product.id)
        mutation = """
        mutation createQRCodeMetaobject($metaobject: MetaobjectCreateInput!) {
            metaobjectCreate(metaobject: $metaobject) {
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
            "metaobject": {
                "type": "kiosk_qr_code",
                "handle": f"qr-code-{kiosk.id}-{product.id}",
                "fields": [
                    {"key": "product", "value": product.shopify_id},
                    {"key": "qr_code_url", "value": qr_code_url},
                    {"key": "qr_code_image", "value": file_id},
                    {"key": "kiosk", "value": kiosk.shopify_id},
                    {"key": "image_url", "value": image_url}
                ]
            }
        }

        result = shopify_manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'metaobjectCreate' in result['data']:
            metaobject = result['data']['metaobjectCreate']['metaobject']
            if metaobject and 'id' in metaobject:
                logger.info(f"Successfully created QR code metaobject for product {product.id} in kiosk {kiosk.id}")
                return metaobject['id']
            else:
                logger.error(f"Error creating QR code metaobject: {result['data']['metaobjectCreate'].get('userErrors', [])}")
        else:
            logger.error(f"Unexpected response structure from Shopify API: {result}")
        
        return None

    def update_kiosk_metaobject(self, shopify_manager, kiosk, qr_codes):
        if not qr_codes:
            logger.warning(f"No QR codes to update for kiosk {kiosk.id}")
            return

        logger.info(f"Updating kiosk metaobject for kiosk {kiosk.id} with {len(qr_codes)} QR codes")
        mutation = """
        mutation updateKiosk($id: ID!, $metaobject: MetaobjectUpdateInput!) {
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
            "id": kiosk.shopify_id,
            "metaobject": {
                "fields": [
                    {"key": "qr_codes", "value": json.dumps(qr_codes)},
                ]
            }
        }

        result = shopify_manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'metaobjectUpdate' in result['data']:
            updated_metaobject = result['data']['metaobjectUpdate']['metaobject']
            if updated_metaobject:
                logger.info(f"Successfully updated kiosk metaobject for kiosk {kiosk.id}")
            else:
                logger.error(f"Error updating kiosk metaobject: {result['data']['metaobjectUpdate'].get('userErrors', [])}")
        else:
            logger.error(f"Failed to update kiosk metaobject: {result}")

    def update_product_metafields(self, shopify_manager, product, qr_codes):
        if not qr_codes:
            logger.warning(f"No QR codes to update for product {product.id}")
            return

        logger.info(f"Updating metafields for product {product.id} with {len(qr_codes)} QR codes")
        mutation = """
        mutation updateProductMetafields($input: ProductInput!) {
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
                "id": product.shopify_id,
                "metafields": [
                    {
                        "namespace": "custom",
                        "key": "kiosk_qr_codes",
                        "value": json.dumps(qr_codes),
                        "type": "list.metaobject_reference"
                    }
                ]
            }
        }

        result = shopify_manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'productUpdate' in result['data']:
            updated_product = result['data']['productUpdate']['product']
            if updated_product:
                logger.info(f"Successfully updated metafields for product {product.id}")
            else:
                logger.error(f"Error updating product metafields: {result['data']['productUpdate'].get('userErrors', [])}")
        else:
            logger.error(f"Failed to update product metafields: {result}")
