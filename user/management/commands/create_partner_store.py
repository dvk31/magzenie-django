
#django/user/management/commands/create_partner_store.py

import json
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from user.models import PartnerStore, Role
from user.services.shopify_connection import ShopifyConnectionManager
logger = logging.getLogger(__name__)

User = get_user_model()





class Command(BaseCommand):
    help = 'Create a partner store for an existing Shopify customer and assign them the merchant role'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='The email address of the Shopify customer')
        parser.add_argument('store_name', type=str, help='The name of the partner store')
        parser.add_argument('store_url', type=str, help='The URL of the partner store')

    def handle(self, *args, **options):
        email = options['email']
        store_name = options['store_name']
        store_url = options['store_url']

        with ShopifyConnectionManager() as manager:
            shopify_customer = self.get_shopify_customer(email, manager)
            if not shopify_customer:
                self.stdout.write(self.style.ERROR(f'Shopify customer with email {email} does not exist'))
                return

            django_user = self.get_or_create_django_user(email, shopify_customer['id'])
            if not django_user:
                self.stdout.write(self.style.ERROR(f'Failed to find or create Django user with email {email}'))
                return

            partner_store = self.create_partner_store(django_user, store_name, store_url, manager)
            if partner_store:
                self.assign_merchant_role(django_user, manager)
                self.stdout.write(self.style.SUCCESS(f'Successfully created partner store and assigned merchant role for customer: {email}'))
            else:
                self.stdout.write(self.style.ERROR(f'Failed to create partner store for customer: {email}'))

    def get_shopify_customer(self, email, manager):
        query = """
        query getCustomer($query: String!) {
            customers(first: 1, query: $query) {
                edges {
                    node {
                        id
                        email
                        firstName
                        lastName
                    }
                }
            }
        }
        """
        variables = {"query": f"email:{email}"}
        result = manager.execute_graphql_query(query, variables)

        if result and 'data' in result and 'customers' in result['data']:
            customers = result['data']['customers']['edges']
            if customers:
                return customers[0]['node']
        
        return None

    def get_or_create_django_user(self, email, shopify_customer_id):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'shopify_customer_id': shopify_customer_id
            }
        )
        if not created:
            user.shopify_customer_id = shopify_customer_id
            user.save()
        return user

    def assign_merchant_role(self, customer, manager):
            merchant_role = self.get_or_create_merchant_role(manager)

            if not merchant_role:
                logger.error(f"Failed to create or get merchant role for customer {customer.email}")
                return

            mutation = """
            mutation customerUpdate($input: CustomerInput!) {
                customerUpdate(input: $input) {
                    customer {
                        id
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """

            current_roles = list(customer.roles.values_list('shopify_id', flat=True))
            current_roles.append(merchant_role.shopify_id)

            variables = {
                "input": {
                    "id": customer.shopify_customer_id,
                    "metafields": [
                        {
                            "namespace": "custom",
                            "key": "roles",
                            "value": json.dumps(current_roles),
                            "type": "list.metaobject_reference"
                        }
                    ]
                }
            }

            result = manager.execute_graphql_query(mutation, variables)
            if result and 'data' in result and 'customerUpdate' in result['data']:
                logger.info(f"Assigned merchant role to customer {customer.email}")
                customer.roles.add(merchant_role)
            else:
                logger.error(f"Failed to assign merchant role to customer {customer.email}: {result}")



    def create_partner_store(self, customer, store_name, store_url, manager):
        try:
            # First, fetch the metaobject definition for partner_store
            query = """
            query {
            metaobjectDefinitions(first: 10) {
                edges {
                node {
                    type
                    fieldDefinitions {
                    name
                    key
                    type {
                        name
                    }
                    }
                }
                }
            }
            }
            """
            
            result = manager.execute_graphql_query(query)
            
            if result is None or 'data' not in result or 'metaobjectDefinitions' not in result['data']:
                logger.error(f"Failed to fetch metaobject definitions: {result}")
                return None
            
            partner_store_definition = next((node['node'] for node in result['data']['metaobjectDefinitions']['edges'] if node['node']['type'].lower() == 'partner_store'), None)
            
            if not partner_store_definition:
                logger.error("PARTNER_STORE metaobject definition not found")
                return None
            
            field_keys = {fd['name'].lower(): {'key': fd['key'], 'type': fd['type']['name']} for fd in partner_store_definition['fieldDefinitions']}
            
            # Now create the partner store using the correct field keys
            mutation = """
            mutation createPartnerStore($metaobject: MetaobjectCreateInput!) {
                metaobjectCreate(metaobject: $metaobject) {
                    metaobject {
                        id
                        handle
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """
            
            fields = []
            
            if 'name' in field_keys:
                fields.append({"key": field_keys['name']['key'], "value": store_name})
            
            if 'store url' in field_keys:
                fields.append({"key": field_keys['store url']['key'], "value": store_url})
            
            if 'owner' in field_keys:
                if field_keys['owner']['type'] == 'customer_reference':
                    fields.append({"key": field_keys['owner']['key'], "value": customer.shopify_customer_id})
                else:
                    logger.warning(f"Owner field is not a customer reference. Type: {field_keys['owner']['type']}")
            
            # Add optional fields if they exist
            optional_fields = ['logo', 'kiosks']
            for field in optional_fields:
                if field in field_keys:
                    if field_keys[field]['type'] in ['file_reference', 'list.metaobject_reference']:
                        fields.append({"key": field_keys[field]['key'], "value": ""})
            
            variables = {
                "metaobject": {
                    "type": "partner_store",
                    "fields": fields
                }
            }

            logger.info(f"Sending GraphQL mutation to create partner store: {store_name}")
            result = manager.execute_graphql_query(mutation, variables)
            logger.info(f"Received response from Shopify: {result}")

            if result is None or 'data' not in result or 'metaobjectCreate' not in result['data']:
                logger.error(f"Unexpected response structure from Shopify: {result}")
                return None

            metaobject_create = result['data']['metaobjectCreate']

            if metaobject_create['metaobject']:
                shopify_store_id = metaobject_create['metaobject']['id']
                partner_store = PartnerStore.objects.create(
                    shopify_id=shopify_store_id,
                    name=store_name,
                    store_url=store_url,
                    owner=customer
                )
                logger.info(f"Created partner store in Shopify and Django: {partner_store.name} (ID: {partner_store.id})")
                return partner_store
            else:
                errors = metaobject_create.get('userErrors', [])
                logger.error(f"Failed to create partner store in Shopify: {errors}")
                return None

        except Exception as e:
            logger.error(f"Error creating partner store in Shopify: {str(e)}")
            logger.debug(traceback.format_exc())
        return None

    def get_or_create_merchant_role(self, manager):
            try:
                return Role.objects.get(name="Merchant")
            except Role.DoesNotExist:
                mutation = """
                mutation createRole($input: MetaobjectCreateInput!) {
                    metaobjectCreate(metaobject: $input) {
                        metaobject {
                            id
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
                        "type": "role",
                        "fields": [
                            {"key": "name", "value": "Merchant"},
                            {"key": "description", "value": "Partner store owner role"},
                            {"key": "permissions", "value": json.dumps(["manage_store", "view_products", "edit_products"])}
                        ]
                    }
                }

                result = manager.execute_graphql_query(mutation, variables)
                if result and 'data' in result and 'metaobjectCreate' in result['data']:
                    metaobject_create = result['data']['metaobjectCreate']
                    if metaobject_create.get('metaobject'):
                        role_id = metaobject_create['metaobject']['id']
                        role = Role.objects.create(
                            shopify_id=role_id,
                            name="Merchant",
                            description="Partner store owner role"
                        )
                        logger.info(f"Successfully created merchant role: {role_id}")
                        return role
                    else:
                        user_errors = metaobject_create.get('userErrors', [])
                        logger.error(f"Failed to create merchant role. User errors: {user_errors}")
                else:
                    logger.error(f"Failed to create merchant role. Unexpected response: {result}")
            
            return None