import logging
from django.core.management.base import BaseCommand
from django.conf import settings
import shopify
from shopify.session import ValidationException
from shopify import ShopifyResource

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test Shopify API connection and customer creation'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None

    def handle(self, *args, **options):
        logger.info('Testing Shopify API connection...')
        
        self.initialize_shopify_session()
        
        try:
            self.test_connection()
            self.test_customer_creation()
        except Exception as e:
            logger.exception("An unexpected error occurred during Shopify tests")
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred: {str(e)}"))
        finally:
            self.close_shopify_session()

    def initialize_shopify_session(self):
        logger.debug(f"SHOPIFY_STORE_URL: {settings.SHOPIFY_STORE_URL}")
        logger.debug(f"SHOPIFY_API_VERSION: {settings.SHOPIFY_API_VERSION}")
        logger.debug(f"SHOPIFY_ADMIN_ACCESS_TOKEN: {settings.SHOPIFY_ADMIN_ACCESS_TOKEN[:5]}...")  # Only log first 5 chars for security

        try:
            self.session = shopify.Session(
                settings.SHOPIFY_STORE_URL,
                settings.SHOPIFY_API_VERSION,
                settings.SHOPIFY_ADMIN_ACCESS_TOKEN
            )
            shopify.ShopifyResource.activate_session(self.session)
            logger.info("Shopify session initialized successfully")
        except ValidationException as e:
            logger.error(f"Failed to initialize Shopify session: {str(e)}")
            raise

    def close_shopify_session(self):
        if self.session:
            shopify.ShopifyResource.clear_session()
            logger.info("Shopify session closed")

    def test_connection(self):
        try:
            shop = shopify.Shop.current()
            logger.info(f"Successfully connected to Shopify store: {shop.name}")
            self.stdout.write(self.style.SUCCESS(f"Successfully connected to Shopify store: {shop.name}"))
        except ShopifyResource.ConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Connection error: {str(e)}"))
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Shopify: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Failed to connect to Shopify: {str(e)}"))
            raise

    def test_customer_creation(self):
        logger.info('Testing customer creation...')
        try:
            customer = self.create_test_customer()
            # The deletion of the test customer is now commented out
            # self.delete_test_customer(customer)
        except Exception as e:
            logger.error(f"Customer creation test failed: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Customer creation test failed: {str(e)}"))
            raise

    def create_test_customer(self):
        customer = shopify.Customer()
        customer.first_name = "Test"
        customer.last_name = "User"
        customer.email = "testuser@example.com"
        
        if customer.save():
            logger.info(f"Successfully created customer with ID: {customer.id}")
            self.stdout.write(self.style.SUCCESS(f"Successfully created customer with ID: {customer.id}"))
            return customer
        else:
            error_message = customer.errors.full_messages()
            logger.error(f"Failed to create customer: {error_message}")
            self.stdout.write(self.style.ERROR(f"Failed to create customer: {error_message}"))
            raise Exception(f"Failed to create customer: {error_message}")

    # The delete_test_customer method is now commented out
    """
    def delete_test_customer(self, customer):
        if customer.destroy():
            logger.info("Test customer deleted successfully")
            self.stdout.write(self.style.SUCCESS("Test customer deleted successfully"))
        else:
            logger.warning("Failed to delete test customer")
            self.stdout.write(self.style.WARNING("Failed to delete test customer"))
    """