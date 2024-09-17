# myapp/management/commands/create_kiosk_qrcode.py

from django.core.management.base import BaseCommand
from django.db import transaction
from user.models import Kiosk, Product, KioskQRCode
from user.services.qr_code_service import QRCodeService
import logging
import uuid

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate or update QR codes for all products in a given kiosk'

    def add_arguments(self, parser):
        parser.add_argument('kiosk_id', type=uuid.UUID, help='UUID of the kiosk')
        parser.add_argument('--force-update', action='store_true', help='Force update of existing QR codes')

    @transaction.atomic
    def handle(self, *args, **options):
        kiosk_id = options['kiosk_id']
        force_update = options['force_update']

        try:
            kiosk = Kiosk.objects.get(id=kiosk_id)
        except Kiosk.DoesNotExist:
            logger.error(f'Kiosk with ID {kiosk_id} does not exist')
            self.stderr.write(self.style.ERROR(f'Kiosk with ID {kiosk_id} does not exist'))
            return

        qr_code_service = QRCodeService()
        products = Product.objects.filter(kiosks=kiosk, is_kiosk_active=True)

        logger.info(f"Processing QR codes for Kiosk: {kiosk.name} (ID: {kiosk.id})")
        self.stdout.write(f"Processing QR codes for Kiosk: {kiosk.name} (ID: {kiosk.id})")

        for product in products:
            logger.info(f"Processing product: {product.title} (ID: {product.id})")
            self.stdout.write(f"Processing product: {product.title} (ID: {product.id})")

            try:
                kiosk_qr_code = qr_code_service.get_or_create_qr_code(kiosk, product, force_update=force_update)
                
                if kiosk_qr_code:
                    product.kiosk_qr_codes.add(kiosk_qr_code)
                    logger.info(f"QR code created/updated for product {product.id}")
                    self.stdout.write(self.style.SUCCESS(f"QR code created/updated for product {product.id}"))
                else:
                    logger.warning(f"Failed to create/update QR code for product {product.id}")
                    self.stdout.write(self.style.WARNING(f"Failed to create/update QR code for product {product.id}"))
            
            except Exception as e:
                logger.exception(f"Error processing product {product.id}: {str(e)}")
                self.stderr.write(self.style.ERROR(f"Error processing product {product.id}: {str(e)}"))

        logger.info(f"Finished processing QR codes for Kiosk {kiosk.id}")
        self.stdout.write(self.style.SUCCESS(f"Finished processing QR codes for Kiosk {kiosk.id}"))