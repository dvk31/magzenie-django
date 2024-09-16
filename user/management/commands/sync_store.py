import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from user.services.shopify_connection import ShopifyConnectionManager
from user.models import PartnerStore, UsersModel

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync Shopify data to Django models for PartnerStore and UsersModel'

    def handle(self, *args, **options):
        with ShopifyConnectionManager() as manager:
            self.sync_partner_stores(manager)
            self.sync_users(manager)

        self.stdout.write(self.style.SUCCESS('Shopify data sync for PartnerStore and UsersModel completed successfully'))

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

        if not result or 'data' not in result or 'metaobjects' not in result['data']:
            logger.error("No data returned from Shopify for partner stores")
            return

        for edge in result['data']['metaobjects']['edges']:
            store_data = {field['key'].lower(): field['value'] for field in edge['node']['fields']}
            logger.debug(f"Processing store data: {store_data}")

            name = store_data.get('name')
            store_url = store_data.get('store url')
            owner_id = store_data.get('owner')

            if not name:
                logger.warning(f"PartnerStore with id {edge['node']['id']} has no 'Name' field. Skipping.")
                continue

            if not store_url:
                logger.warning(f"PartnerStore '{name}' with id {edge['node']['id']} has no 'Store URL'. Setting to None.")
                store_url = None  # Or set a default URL if applicable

            try:
                owner = UsersModel.objects.get(shopify_customer_id=owner_id)
            except UsersModel.DoesNotExist:
                logger.warning(f"No user found with Shopify customer ID {owner_id} for PartnerStore {name}")
                continue

            partner_store, created = PartnerStore.objects.update_or_create(
                shopify_id=edge['node']['id'],
                defaults={
                    'name': name,
                    'store_url': store_url,
                    'owner': owner,
                }
            )

            if created:
                logger.info(f"Created new PartnerStore: {partner_store}")
            else:
                logger.info(f"Updated existing PartnerStore: {partner_store}")

        self.stdout.write(self.style.SUCCESS(f"Synced {len(result['data']['metaobjects']['edges'])} partner stores"))

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

        if not result or 'data' not in result or 'customers' not in result['data']:
            logger.error("No data returned from Shopify for users")
            return

        for edge in result['data']['customers']['edges']:
            customer_data = edge['node']
            metafields = {mf['node']['key']: mf['node']['value'] for mf in customer_data['metafields']['edges']}

            user, created = UsersModel.objects.update_or_create(
                shopify_customer_id=customer_data['id'],
                defaults={
                    'email': customer_data['email'],
                    'first_name': customer_data['firstName'],
                    'last_name': customer_data['lastName'],
                    'phone_number': customer_data['phone'],
                    'is_partner': metafields.get('is_partner') == 'true',
                    'partner_store_id': metafields.get('partner_store_id'),
                    'username': customer_data['email'],  
                }
            )

            if created:
                logger.info(f"Created new user: {user}")
            else:
                logger.info(f"Updated existing user: {user}")