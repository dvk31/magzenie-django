import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from user.models import Product
from user.services.shopify_connection import ShopifyConnectionManager
from user.services.get_content_url import get_shopify_video_url, get_shopify_thumbnail_url

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync Shopify products to Django models'

    @transaction.atomic
    def handle(self, *args, **options):
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
            
            # Get the video and thumbnail URLs using the helper functions
            video_url = get_shopify_video_url(product_data['id'])
            thumbnail_url = get_shopify_thumbnail_url(product_data['id'])
            
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