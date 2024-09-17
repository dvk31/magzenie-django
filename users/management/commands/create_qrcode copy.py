import logging
import traceback
from django.core.management.base import BaseCommand
from user.models import Product, Kiosk, KioskQRCode
from user.services.shopify_connection import ShopifyConnectionManager
from user.services.upload_file import upload_file_to_shopify
from user.services.qrcode import generate_qr_code  # Import the utility function

# Configure logging
logger = logging.getLogger(__name__)





logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate QR codes for kiosk-product combinations, upload to Shopify, and sync data'

    def add_arguments(self, parser):
        parser.add_argument('store_id', type=str, help='The ID of the store to process')

    def handle(self, *args, **options):
        store_id = options['store_id']
        try:
            kiosks = Kiosk.objects.filter(store_id=store_id)
            logger.info(f"Starting QR code generation for {kiosks.count()} kiosks in store {store_id}.")
            
            with ShopifyConnectionManager() as manager:
                for kiosk in kiosks:
                    try:
                        self.process_kiosk(kiosk, manager)
                    except Exception as e:
                        logger.error(f"Error processing kiosk {kiosk.id}: {str(e)}")
                        logger.debug(traceback.format_exc())

            self.stdout.write(self.style.SUCCESS('QR code generation and sync completed successfully'))
            logger.info("QR code generation and sync completed successfully")

        except Exception as e:
            logger.critical(f"Critical error in handle method: {str(e)}")
            logger.debug(traceback.format_exc())
            self.stdout.write(self.style.ERROR('An error occurred during the QR code generation process'))

    def process_kiosk(self, kiosk, manager):
        for product in kiosk.products.all():
            try:
                self.process_kiosk_product(kiosk, product, manager)
            except Exception as e:
                logger.error(f"Error processing product {product.id} for kiosk {kiosk.id}: {str(e)}")
                logger.debug(traceback.format_exc())

    def process_kiosk_product(self, kiosk, product, manager):
        try:
            # Check if QR code already exists
            kiosk_qr_code, created = KioskQRCode.objects.get_or_create(kiosk=kiosk, product=product)
            
            if not created and kiosk_qr_code.qr_code_url:
                logger.info(f"QR code already exists for kiosk {kiosk.id} and product {product.id}. Skipping creation.")
                return

            relative_url = get_qr_code_url(kiosk.id, product.id)
            qr_code_image = generate_qr_code(relative_url)
            
            file_id = upload_file_to_shopify(
                file_content=qr_code_image.getvalue(),
                filename=f"qr_code_kiosk_{kiosk.id}_product_{product.id}.png",
                file_type="image/png",
                product_id=product.id,
                manager=manager
            )
            if file_id:
                stored_url = self.generate_stored_url(kiosk.id, product.id)
                metafield_id = self.update_shopify_metafield(kiosk, product, stored_url, manager)
                if metafield_id:
                    self.update_django_model(kiosk_qr_code, stored_url)
                else:
                    logger.warning(f"Failed to update metafield for kiosk {kiosk.id} and product {product.id}")
            else:
                logger.warning(f"Failed to upload QR code for kiosk {kiosk.id} and product {product.id}")

        except Exception as e:
            logger.error(f"Error in process_kiosk_product for kiosk {kiosk.id} and product {product.id}: {str(e)}")
            logger.debug(traceback.format_exc())
            self.stdout.write(self.style.WARNING(f"Failed to process kiosk {kiosk.id} and product {product.id}"))

    def generate_stored_url(self, kiosk_id, product_id):
        return f"https://cdn.shopify.com/s/files/1/0887/4455/8865/files/qr_code_kiosk_{kiosk_id}_product_{product_id}.png?v=1723329521"

    def update_shopify_metafield(self, kiosk, product, file_url, manager):
        try:
            mutation = """
            mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
                metafieldsSet(metafields: $metafields) {
                    metafields {
                        id
                        key
                        value
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """
            
            variables = {
                "metafields": [{
                    "ownerId": kiosk.shopify_id,
                    "namespace": "custom",
                    "key": f"qr_code_product_{product.id}",
                    "type": "url",
                    "value": file_url
                }]
            }
            
            result = manager.execute_graphql_query(mutation, variables)
            logger.debug(f"GraphQL mutation response: {result}")

            if result is None:
                logger.error(f"GraphQL mutation for setting metafield returned None for kiosk {kiosk.id} and product {product.id}")
                return None

            if result.get('data', {}).get('metafieldsSet', {}).get('metafields'):
                logger.info(f"Successfully set metafield for kiosk {kiosk.id} and product {product.id}")
                return result['data']['metafieldsSet']['metafields'][0]['id']
            else:
                error_message = result.get('data', {}).get('metafieldsSet', {}).get('userErrors', [])
                logger.warning(f"Failed to set metafield for kiosk {kiosk.id} and product {product.id}: {error_message}")
                return None

        except Exception as e:
            logger.error(f"Error updating metafield for kiosk {kiosk.id} and product {product.id}: {str(e)}")
            logger.debug(traceback.format_exc())
            return None

    def update_django_model(self, kiosk_qr_code, file_url):
        try:
            if kiosk_qr_code.qr_code_url != file_url:
                kiosk_qr_code.qr_code_url = file_url
                kiosk_qr_code.save()
                self.stdout.write(self.style.SUCCESS(f"Updated QR code URL for kiosk {kiosk_qr_code.kiosk.id} and product {kiosk_qr_code.product.id}"))
                logger.info(f"Updated Django model for kiosk {kiosk_qr_code.kiosk.id} and product {kiosk_qr_code.product.id}")
            else:
                logger.info(f"QR code URL for kiosk {kiosk_qr_code.kiosk.id} and product {kiosk_qr_code.product.id} is already up to date")

        except Exception as e:
            logger.error(f"Error updating Django model for kiosk {kiosk_qr_code.kiosk.id} and product {kiosk_qr_code.product.id}: {str(e)}")
            logger.debug(traceback.format_exc())
            raise