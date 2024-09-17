from django.core.management.base import BaseCommand
from django.db import transaction
from user.models import PartnerStore, Kiosk, Product, KioskQRCode
from user.services.kiosk_service import KioskService
from user.services.kiosk_qr_code_association_service import KioskQRCodeAssociationService
from user.services.product_qr_code_association_service import ProductQRCodeAssociationService
from user.services.shopify_connection import ShopifyConnectionManager
import logging
import json
import uuid

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Creates a new kiosk for a given store, sets up all necessary associations, loads products, generates QR codes, and updates Shopify IDs'

    def add_arguments(self, parser):
        parser.add_argument('store_id', type=str, help='The UUID of the PartnerStore to create a kiosk for')
        parser.add_argument('--products-file', type=str, default='shopify_products.json', help='Path to the JSON file containing product data')

    def load_products_from_json(self, file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Error loading products from JSON: {str(e)}")
            return []

    @transaction.atomic
    def handle(self, *args, **options):
        store_id = options['store_id']
        products_file = options['products_file']

        try:
            store_uuid = uuid.UUID(store_id)
            store = PartnerStore.objects.get(id=store_uuid)
        except ValueError:
            self.stdout.write(self.style.ERROR(f'Invalid UUID format: {store_id}'))
            return
        except PartnerStore.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'PartnerStore with UUID {store_id} does not exist'))
            return

        self.stdout.write(self.style.SUCCESS(f'Creating kiosk for store: {store.name}'))

        kiosk_service = KioskService(store.id)

        try:
            kiosk = kiosk_service.create_and_setup_kiosk()

            if kiosk:
                self.stdout.write(self.style.SUCCESS(f'Successfully created and set up kiosk: {kiosk.name} (ID: {kiosk.id})'))
                
                # Load and associate products
                products_data = self.load_products_from_json(products_file)
                associated_products = self.associate_products_with_kiosk(kiosk, products_data)
                
                # Explicitly update kiosk metafields with associated products
                kiosk_service.association_service._update_kiosk_metafields(kiosk)
                
                # Generate and associate QR codes for the kiosk
                kiosk_qr_code_service = KioskQRCodeAssociationService(kiosk.id)
                qr_codes = kiosk_qr_code_service.create_and_associate_qr_codes()
                
                # Update Shopify IDs for QR codes
                self.update_qr_code_shopify_ids(kiosk, qr_codes)
                
                # Generate and associate QR codes for products
                product_qr_code_service = ProductQRCodeAssociationService(kiosk.id)
                product_qr_code_service.associate_qr_codes_to_products()
                
                # Log kiosk details
                self.log_kiosk_details(kiosk, associated_products)
            else:
                self.stdout.write(self.style.ERROR('Failed to create kiosk'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred while creating the kiosk: {str(e)}'))
            logger.exception('Error in create_kiosk command')

        self.stdout.write(self.style.SUCCESS('Command completed'))

    def associate_products_with_kiosk(self, kiosk, products_data):
        associated_products = []
        for product_data in products_data:
            try:
                product, created = Product.objects.update_or_create(
                    shopify_id=product_data['shopify_id'],
                    defaults={'title': product_data['title']}
                )
                kiosk.products.add(product)
                associated_products.append(product)
                self.stdout.write(f"Associated product: {product.title}")
            except Exception as e:
                logger.error(f"Error associating product {product_data.get('title', 'Unknown')}: {str(e)}")
        return associated_products

    def update_qr_code_shopify_ids(self, kiosk, qr_codes):
        shopify_connection = ShopifyConnectionManager()
        query = """
        query getKioskQRCodes($id: ID!) {
            metaobject(id: $id) {
                fields {
                    key
                    value
                }
            }
        }
        """
        variables = {
            "id": kiosk.shopify_id
        }
        result = shopify_connection.execute_graphql_query(query, variables)
        
        if result and 'data' in result and 'metaobject' in result['data']:
            fields = result['data']['metaobject']['fields']
            qr_codes_field = next((field for field in fields if field['key'] == 'qr_codes'), None)
            
            if qr_codes_field and qr_codes_field['value']:
                shopify_qr_codes = json.loads(qr_codes_field['value'])
                
                for local_qr_code, shopify_qr_code_id in zip(qr_codes, shopify_qr_codes):
                    local_qr_code.shopify_id = shopify_qr_code_id
                    local_qr_code.save()
                    self.stdout.write(self.style.SUCCESS(f'Updated Shopify ID for QR code: {local_qr_code.id}'))
            else:
                self.stdout.write(self.style.WARNING('No QR codes found in Shopify metaobject'))
        else:
            self.stdout.write(self.style.ERROR('Failed to fetch QR codes from Shopify'))

    def log_kiosk_details(self, kiosk, associated_products):
        self.stdout.write(f'Kiosk details:')
        self.stdout.write(f'  - Shopify ID: {kiosk.shopify_id}')
        self.stdout.write(f'  - Is active: {kiosk.is_active}')
        self.stdout.write(f'  - Associated store: {kiosk.store.name} (ID: {kiosk.store.id})')
        
        if kiosk.collection:
            self.stdout.write(f'  - Associated collection: {kiosk.collection.name} (ID: {kiosk.collection.id})')
        else:
            self.stdout.write(f'  - No associated collection')

        self.stdout.write(f'  - Number of associated products: {len(associated_products)}')
        for product in associated_products:
            self.stdout.write(f'    - {product.title} (Shopify ID: {product.shopify_id})')
        
        self.stdout.write(f'  - Number of QR codes: {kiosk.kiosk_qr_codes.count()}')
        self.stdout.write(f'  - Kiosk QR code URL: {kiosk.qr_code_url}')