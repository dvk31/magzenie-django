import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from user.services.shopify_connection import ShopifyConnectionManager
from user.models import PartnerStore, Kiosk, Product, UsersModel
from django.conf import settings


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync Shopify data to Django models for PartnerStore, Kiosk, Product, and UsersModel'

    def handle(self, *args, **options):
        with ShopifyConnectionManager() as manager:
            self.sync_partner_stores(manager)
            self.sync_kiosks(manager)
            self.sync_products()
            self.sync_users(manager)

        self.stdout.write(self.style.SUCCESS('Shopify data sync completed successfully'))

    @transaction.atomic
    def sync_partner_stores(self, manager):
        query = """
        query {
          metaobjects(type: "PARTNER_STORE", first: 100) {
            edges {
              node {
                id
                fields {
                  key
                  value
                }
              }
            }
          }
        }
        """
        result = manager.execute_graphql_query(query)
        
        for edge in result['data']['metaobjects']['edges']:
            store_data = {field['key']: field['value'] for field in edge['node']['fields']}
            name = store_data.get('Name')
            store_url = store_data.get('Store URL')

            if not name:
                logger.warning(f"Skipping PartnerStore with id {edge['node']['id']} due to missing 'Name' field")
                continue

            PartnerStore.objects.update_or_create(
                shopify_id=edge['node']['id'],
                defaults={
                    'name': name,
                    'store_url': store_url,
                }
            )
        self.stdout.write(self.style.SUCCESS(f"Synced {len(result['data']['metaobjects']['edges'])} partner stores"))

    @transaction.atomic
    def sync_kiosks(self, manager):
        query = """
        query {
          metaobjects(type: "KIOSK", first: 100) {
            edges {
              node {
                id
                fields {
                  key
                  value
                }
              }
            }
          }
        }
        """
        result = manager.execute_graphql_query(query)
        
        for edge in result['data']['metaobjects']['edges']:
            kiosk_data = {field['key']: field['value'] for field in edge['node']['fields']}
            name = kiosk_data.get('Name')
            kiosk_qr_code_url = kiosk_data.get('kiosk_qr_code_url')
            is_active = kiosk_data.get('is_active') == 'true'

            if not name:
                logger.warning(f"Skipping Kiosk with id {edge['node']['id']} due to missing 'Name' field")
                continue

            Kiosk.objects.update_or_create(
                shopify_id=edge['node']['id'],
                defaults={
                    'name': name,
                    'kiosk_qr_code_url': kiosk_qr_code_url,
                    'is_active': is_active,
                }
            )
        self.stdout.write(self.style.SUCCESS(f"Synced {len(result['data']['metaobjects']['edges'])} kiosks"))






    @transaction.atomic
    def sync_products(self):
        query = """
        query {
        products(first: 100) {
            edges {
            node {
                id
                title
                description
                priceRange {
                minVariantPrice {
                    amount
                }
                }
                metafields(first: 10) {
                edges {
                    node {
                    key
                    value
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
            metafields = {mf['node']['key']: mf['node']['value'] for mf in product_data['metafields']['edges']}
            
            # Get the video and thumbnail URLs
            try:
                video_url = get_shopify_content_url(content_type='video')
                thumbnail_url = get_shopify_content_url(content_type='thumbnail')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error fetching content URLs for product {product_data['id']}: {str(e)}"))
                video_url = None
                thumbnail_url = None
            
            Product.objects.update_or_create(
                shopify_id=product_data['id'],
                defaults={
                    'title': product_data['title'],
                    'description': product_data['description'],
                    'price': product_data['priceRange']['minVariantPrice']['amount'],
                    'video_url': video_url,
                    'thumbnail_url': thumbnail_url,
                    'qr_code_url': metafields.get('qr_code'),
                    'kiosk_video': metafields.get('kiosk_video'),
                }
            )
        self.stdout.write(self.style.SUCCESS(f"Synced {len(result['data']['products']['edges'])} products"))


    @transaction.atomic
    def sync_users(self, manager):
        query = """
        query {
          customers(first: 100) {
            edges {
              node {
                id
                email
                firstName
                lastName
                phone
                metafields(first: 10) {
                  edges {
                    node {
                      key
                      value
                    }
                  }
                }
              }
            }
          }
        }
        """
        result = manager.execute_graphql_query(query)
        
        for edge in result['data']['customers']['edges']:
            customer_data = edge['node']
            metafields = {mf['node']['key']: mf['node']['value'] for mf in customer_data['metafields']['edges']}
            
            UsersModel.objects.update_or_create(
                shopify_customer_id=customer_data['id'],
                defaults={
                    'email': customer_data['email'],
                    'first_name': customer_data['firstName'],
                    'last_name': customer_data['lastName'],
                    'phone_number': customer_data['phone'],
                    'is_partner': metafields.get('is_partner') == 'true',
                    'partner_store_id': metafields.get('partner_store_id'),
                    'username': customer_data['email'],  # Assuming email is used as username
                }
            )
        self.stdout.write(self.style.SUCCESS(f"Synced {len(result['data']['customers']['edges'])} users"))