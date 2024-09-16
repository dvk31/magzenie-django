# user/management/commands/test_shopify_customer_creation.py

import json
import logging
import traceback
from django.core.management.base import BaseCommand
from user.services.shopify_connection import ShopifyConnectionManager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test Shopify customer creation using GraphQL'

    def handle(self, *args, **options):
        try:
            with ShopifyConnectionManager() as manager:
                mutation = """
                mutation customerCreate($input: CustomerCreateInput!) {
                  customerCreate(input: $input) {
                    customer {
                      id
                      email
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
                        "email": "testcustomer@example.com",  # Replace with a unique test email
                        "firstName": "Test",
                        "lastName": "Customer",
                        "password": "YourStrongPassword",  # Replace with a strong password
                        "passwordConfirmation": "YourStrongPassword",
                        "phone": "+15555555555",  # Replace with a valid phone number if needed
                        "acceptsMarketing": False
                    }
                }
                result = manager.execute_graphql_query(mutation, variables)
                
                if result:
                    if 'data' in result and 'customerCreate' in result['data'] and 'customer' in result['data']['customerCreate']:
                        customer = result['data']['customerCreate']['customer']
                        self.stdout.write(self.style.SUCCESS(f"Customer created successfully: {customer}"))
                    else:
                        errors = result['data']['customerCreate'].get('userErrors', [])
                        self.stdout.write(self.style.ERROR(f"Failed to create customer: {errors}"))
                else:
                    self.stdout.write(self.style.ERROR("GraphQL query failed or returned an unexpected response."))

        except Exception as e:
            logger.critical(f"Critical error in handle method: {str(e)}")
            logger.debug(traceback.format_exc())
            self.stdout.write(self.style.ERROR('An error occurred during the test.'))