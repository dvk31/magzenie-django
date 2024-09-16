import logging
from django.conf import settings
from .shopify_connection import ShopifyConnectionManager
import json

logger = logging.getLogger(__name__)

class ShopifyCustomerManager:
    def __init__(self):
        self.connection = None

    def __enter__(self):
        self.connection = ShopifyConnectionManager()
        self.connection.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.__exit__(exc_type, exc_val, exc_tb)
        self.connection = None


    def create_customer(self, first_name, last_name, email, merchant_ids, **kwargs):
        try:
            customer_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "metafields": [
                    {
                        "key": "merchant_ids",
                        "value": json.dumps(list(set(merchant_ids))),  # Ensure unique IDs
                        "value_type": "json_string",
                        "namespace": "peeqshop"
                    }
                ],
                **kwargs
            }
            customer = self.connection.admin_api_call('Customer', 'create', customer_data)
            if customer.errors:
                raise Exception(f"Failed to create customer: {customer.errors.full_messages()}")
            logger.info(f"Successfully created customer with ID: {customer.id}")
            return customer
        except Exception as e:
            logger.error(f"Error creating customer: {str(e)}")
            raise

    def update_customer_merchants(self, customer_id, merchant_ids):
        try:
            customer = self.connection.admin_api_call('Customer', 'find', customer_id)
            metafields = customer.metafields()
            merchant_metafield = next((m for m in metafields if m.key == 'merchant_ids'), None)
            
            if merchant_metafield:
                existing_ids = json.loads(merchant_metafield.value)
                updated_ids = list(set(existing_ids + merchant_ids))  # Combine and ensure uniqueness
                merchant_metafield.value = json.dumps(updated_ids)
            else:
                customer.add_metafield(
                    shopify.Metafield({
                        'key': 'merchant_ids',
                        'value': json.dumps(list(set(merchant_ids))),
                        'value_type': 'json_string',
                        'namespace': 'peeqshop'
                    })
                )

            if customer.save():
                logger.info(f"Successfully updated merchant IDs for customer with ID: {customer.id}")
                return customer
            else:
                raise Exception(f"Failed to update customer: {customer.errors.full_messages()}")
        except Exception as e:
            logger.error(f"Error updating customer merchant IDs: {str(e)}")
            raise

    def get_customer_merchant_ids(self, customer_id):
        try:
            customer = self.connection.admin_api_call('Customer', 'find', customer_id)
            metafields = customer.metafields()
            merchant_metafield = next((m for m in metafields if m.key == 'merchant_ids'), None)
            if merchant_metafield:
                return json.loads(merchant_metafield.value)
            return []
        except Exception as e:
            logger.error(f"Error retrieving customer merchant IDs: {str(e)}")
            raise

    def delete_customer(self, customer_id):
        try:
            customer = self.connection.admin_api_call('Customer', 'find', customer_id)
            if customer.destroy():
                logger.info(f"Successfully deleted customer with ID: {customer_id}")
                return True
            else:
                raise Exception("Failed to delete customer")
        except Exception as e:
            logger.error(f"Error deleting customer: {str(e)}")
            raise

    def get_customer(self, customer_id):
        try:
            customer = self.connection.admin_api_call('Customer', 'find', customer_id)
            logger.info(f"Successfully retrieved customer with ID: {customer_id}")
            return customer
        except Exception as e:
            logger.error(f"Error retrieving customer: {str(e)}")
            raise

    def search_customers(self, **kwargs):
        try:
            customers = self.connection.admin_api_call('Customer', 'search', **kwargs)
            logger.info(f"Successfully searched for customers with criteria: {kwargs}")
            return customers
        except Exception as e:
            logger.error(f"Error searching for customers: {str(e)}")
            raise


