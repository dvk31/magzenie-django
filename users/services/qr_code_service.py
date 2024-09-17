# services/qr_code_service.py

import logging
from user.models import Kiosk, KioskQRCode, Product
from .shopify_connection import ShopifyConnectionManager
from .qrcode import generate_qr_code, get_qr_code_relative_url
from .get_content_url import generate_qr_code_filename, get_qr_code_image_url
from django.conf import settings
import uuid
from .upload_file import upload_file_to_shopify

logger = logging.getLogger(__name__)

class QRCodeService:
    def __init__(self, kiosk_id):
        self.kiosk = Kiosk.objects.get(id=kiosk_id)
        self.manager = ShopifyConnectionManager()

    def generate_and_upload_qr_code(self, product_id):
        try:
            logger.info(f'Generating QR code for product {product_id} in kiosk {self.kiosk.id}')
            product = Product.objects.get(id=product_id)
            relative_url = self._get_qr_code_relative_url(product.shopify_id)
            qr_code_buffer = self._generate_qr_code_image(relative_url)

            file_id = self._upload_qr_code_to_shopify(qr_code_buffer, product_id)
            if not file_id:
                raise Exception("Failed to upload QR code to Shopify")

            qr_code_url = get_qr_code_image_url(self.kiosk.id, product_id)
            image_url = qr_code_url  # Assuming the image_url is the same as qr_code_url
            
            self._create_or_update_kiosk_qr_code(product_id, file_id, qr_code_url, image_url)

            logger.info(f'Successfully created and uploaded QR code for product {product_id} in kiosk {self.kiosk.id}')
            return qr_code_url, file_id, relative_url  # Return URL, file ID, and relative URL
        except Exception as e:
            logger.error(f'Error processing QR code for product {product_id} in kiosk {self.kiosk.id}: {str(e)}', exc_info=True)
            return None, None, None

    def _get_qr_code_relative_url(self, product_shopify_id):
        logger.debug(f'Getting QR code relative URL for product {product_shopify_id}')
        kiosk_id = self.kiosk.shopify_id.split('/')[-1]
        product_id = product_shopify_id.split('/')[-1]
        return f"scan/{kiosk_id}/{product_id}"

    def _generate_qr_code_image(self, relative_url):
        logger.debug(f'Generating QR code image for URL: {relative_url}')
        full_url = f"{settings.PEEQSHOP_DOMAIN}/{relative_url}"
        return generate_qr_code(full_url, settings.PEEQSHOP_DOMAIN)

    def _upload_qr_code_to_shopify(self, qr_code_buffer, product_id):
        logger.debug(f'Uploading QR code to Shopify for product {product_id}')
        filename = generate_qr_code_filename(self.kiosk.id, product_id)
        file_type = 'image/png'
        file_content = qr_code_buffer.getvalue()
        return upload_file_to_shopify(file_content, filename, file_type, self.kiosk.shopify_id, self.manager)

    def _create_or_update_kiosk_qr_code(self, product_id, file_id, scan_url, image_url):
        logger.debug(f'Creating/Updating KioskQRCode for product {product_id}')
        try:
            product = Product.objects.get(id=product_id)
            
            KioskQRCode.objects.update_or_create(
                kiosk=self.kiosk,
                product=product,
                defaults={
                    'shopify_id': file_id,
                    'qr_code_url': scan_url,
                    'image_url': image_url
                }
            )
            logger.info(f'Successfully created/updated KioskQRCode for product {product_id}')
        except Product.DoesNotExist:
            logger.error(f'Product with ID {product_id} does not exist')
        except Exception as e:
            logger.error(f'Error creating/updating KioskQRCode for product {product_id}: {str(e)}', exc_info=True)

