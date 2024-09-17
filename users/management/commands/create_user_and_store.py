import json
import logging
import traceback
from django.core.management.base import BaseCommand
from django.conf import settings
from user.models import UsersModel, Role, PartnerStore
from user.services.shopify_connection import ShopifyConnectionManager
from supabase import create_client 
from gotrue.errors import AuthApiError
import shopify
from shopify.session import ValidationException
from shopify import ShopifyResource
import requests
import uuid

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create or update a user and their associated Partner Store in Shopify and Django'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='The email of the user')
        parser.add_argument('full_name', type=str, help='The full name of the user')
        parser.add_argument('--username', type=str, help='Optional username (defaults to email)', required=False)
        parser.add_argument('--update', action='store_true', help='Update existing user instead of creating new one')

    def handle(self, *args, **options):
        email = options['email']
        full_name = options['full_name']
        username = options.get('username', email)
        update_existing = options['update']
        role_name = "Merchant"  

        try:
            with ShopifyConnectionManager() as shopify_manager:
                # 1. Get or Create Shopify Customer
                shopify_customer_id = self.get_or_create_shopify_customer(email, full_name, update_existing)

                if shopify_customer_id:
                    # 2. Get or Create Partner Store in Shopify
                    store_name = f"{full_name}'s Store"
                    shopify_store_id = self.get_or_create_shopify_store(store_name, shopify_customer_id, shopify_manager)

                    if shopify_store_id:
                        # 3. Create or Update Django User and Associate with Supabase
                        django_user = self.create_or_update_django_user(email, full_name, username, role_name, shopify_customer_id, update_existing)

                        if django_user:
                            # 4. Create or Update Partner Store in Django
                            store_url = f"https://{settings.SHOPIFY_STORE_URL}/admin/customers/{shopify_customer_id}"
                            self.create_or_update_partner_store(shopify_store_id, store_name, django_user, store_url)

                            self.stdout.write(self.style.SUCCESS(
                                f'User "{full_name}" and Partner Store "{store_name}" processed successfully!'
                            ))
                        else:
                            self.stdout.write(self.style.ERROR('Failed to create/update Django user'))
                    else:
                        self.stdout.write(self.style.ERROR('Failed to create/get Partner Store in Shopify'))
                else:
                    self.stdout.write(self.style.ERROR('Failed to get or create Shopify customer'))

        except Exception as e:
            logger.critical(f"Critical error in handle method: {str(e)}")
            logger.debug(traceback.format_exc())
            self.stdout.write(self.style.ERROR('An error occurred during the user/store processing'))
