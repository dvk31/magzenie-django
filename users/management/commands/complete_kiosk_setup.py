import logging
from django.core.management.base import BaseCommand
from user.models import Kiosk, PartnerStore, Collection
from user.services.shopify_connection import ShopifyConnectionManager
import json
import re


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Complete kiosk setup by creating a collection, updating partner store, and customer record'

    def add_arguments(self, parser):
        parser.add_argument('kiosk_id', type=str, help='The ID of the kiosk')

    def handle(self, *args, **options):
        kiosk_id = options['kiosk_id']
        
        try:
            kiosk = Kiosk.objects.get(id=kiosk_id)
        except Kiosk.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Kiosk with ID {kiosk_id} does not exist'))
            return

        self.stdout.write(f'Completing setup for kiosk: {kiosk.name} (ID: {kiosk.id})')

        with ShopifyConnectionManager() as manager:
            collection_id = self.create_collection_for_kiosk(kiosk, manager)
            if collection_id:
                self.update_kiosk_with_collection(kiosk, collection_id, manager)
                self.update_partner_store(kiosk, manager)
                self.update_store_owner_customer_record(kiosk, manager)
                self.stdout.write(self.style.SUCCESS(f'Successfully completed setup for kiosk: {kiosk.name}'))
            else:
                self.stdout.write(self.style.ERROR(f'Failed to create collection for kiosk: {kiosk.name}. Stopping process.'))
                return

    def create_collection_for_kiosk(self, kiosk, manager):
        mutation = """
        mutation createCollection($input: CollectionInput!) {
            collectionCreate(input: $input) {
                collection {
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
                "title": f"Kiosk Collection - {kiosk.name}",
                "descriptionHtml": f"Products for kiosk: {kiosk.name}",
                "metafields": [
                    {
                        "namespace": "custom",
                        "key": "kiosk",
                        "value": kiosk.shopify_id,
                        "type": "metaobject_reference"
                    },
                    {
                        "namespace": "custom",
                        "key": "kiosk_active",
                        "value": "true",
                        "type": "boolean"
                    }
                ]
            }
        }

        result = manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'collectionCreate' in result['data']:
            collection_create = result['data']['collectionCreate']
            if collection_create.get('collection'):
                collection_id = collection_create['collection']['id']
                Collection.objects.create(
                    shopify_id=collection_id,
                    name=f"Kiosk Collection - {kiosk.name}",
                    kiosk=kiosk,
                    is_active=True
                )
                logger.info(f"Successfully created collection for kiosk {kiosk.id}: {collection_id}")
                return collection_id
            else:
                user_errors = collection_create.get('userErrors', [])
                logger.error(f"Failed to create collection for kiosk {kiosk.id}. User errors: {user_errors}")
        else:
            logger.error(f"Failed to create collection for kiosk {kiosk.id}. Unexpected response: {result}")
        
        return None





    def ensure_shopify_gid(self, id_value, resource_type):
        if isinstance(id_value, str) and id_value.startswith('gid://shopify/'):
            logger.info(f"ID already in GID format: {id_value}")
            return id_value
        gid = f"gid://shopify/{resource_type}/{id_value}"
        logger.info(f"Converted ID to GID: {id_value} -> {gid}")
        return gid

    def update_kiosk_with_collection(self, kiosk, collection_id, manager):
        mutation = """
        mutation metaobjectUpdate($id: ID!, $metaobject: MetaobjectUpdateInput!) {
            metaobjectUpdate(id: $id, metaobject: $metaobject) {
                metaobject {
                    id
                    fields {
                        key
                        value
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        kiosk_gid = self.ensure_shopify_gid(kiosk.shopify_id, "Metaobject")
        collection_gid = self.ensure_shopify_gid(collection_id, "Collection")
        
        logger.info(f"Updating kiosk: {kiosk_gid} with collection: {collection_gid}")
        
        variables = {
            "id": kiosk_gid,
            "metaobject": {
                "fields": [
                    {
                        "key": "collection",
                        "value": collection_gid
                    }
                ]
            }
        }
        logger.info(f"Mutation variables: {variables}")
        result = manager.execute_graphql_query(mutation, variables)
        logger.info(f"GraphQL result: {result}")
        
        if result and 'data' in result and 'metaobjectUpdate' in result['data']:
            metaobject_update = result['data']['metaobjectUpdate']
            if not metaobject_update.get('userErrors'):
                logger.info(f"Successfully updated kiosk {kiosk.id} with collection {collection_id}")
                
                # Extract the collection ID from the GID
                collection_id_raw = self.extract_id_from_gid(collection_id)
                
                # Try to get the Collection object, or create it if it doesn't exist
                try:
                    collection = Collection.objects.get(shopify_id=collection_id_raw)
                except Collection.DoesNotExist:
                    collection_name = f"Kiosk Collection - {kiosk.name}"
                    collection = Collection.objects.create(
                        shopify_id=collection_id_raw,
                        name=collection_name,
                        kiosk=kiosk,
                        is_active=True
                    )
                    logger.info(f"Created new Collection object: {collection}")
                
                # Update the kiosk with the collection
                kiosk.collection = collection
                kiosk.save()
                logger.info(f"Updated kiosk {kiosk.id} with collection {collection.id}")
            else:
                logger.error(f"Failed to update kiosk. Error: {metaobject_update['userErrors']}")
        else:
            logger.error(f"Failed to update kiosk {kiosk.id} with collection: {result}")

    def update_partner_store(self, kiosk, manager):
        mutation = """
        mutation metaobjectUpdate($id: ID!, $metaobject: MetaobjectUpdateInput!) {
            metaobjectUpdate(id: $id, metaobject: $metaobject) {
                metaobject {
                    id
                    fields {
                        key
                        value
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        store = kiosk.store
        store_gid = self.ensure_shopify_gid(store.shopify_id, "Metaobject")
        
        # Fetch current kiosks
        current_kiosks_query = """
        query getPartnerStore($id: ID!) {
            metaobject(id: $id) {
                field(key: "kiosks") {
                    value
                }
            }
        }
        """
        current_kiosks_variables = {"id": store_gid}
        current_kiosks_result = manager.execute_graphql_query(current_kiosks_query, current_kiosks_variables)
        
        if current_kiosks_result and 'data' in current_kiosks_result and 'metaobject' in current_kiosks_result['data']:
            current_kiosks_value = current_kiosks_result['data']['metaobject']['field']['value']
            current_kiosks = json.loads(current_kiosks_value) if current_kiosks_value else []
        else:
            current_kiosks = []
        
        kiosk_gid = self.ensure_shopify_gid(kiosk.shopify_id, "Metaobject")
        if kiosk_gid not in current_kiosks:
            current_kiosks.append(kiosk_gid)
        
        logger.info(f"Updating partner store: {store_gid} with kiosks: {current_kiosks}")
        
        variables = {
            "id": store_gid,
            "metaobject": {
                "fields": [
                    {
                        "key": "kiosks",
                        "value": json.dumps(current_kiosks)
                    }
                ]
            }
        }
        logger.info(f"Mutation variables: {variables}")
        result = manager.execute_graphql_query(mutation, variables)
        logger.info(f"GraphQL result: {result}")
        if result and 'data' in result and 'metaobjectUpdate' in result['data']:
            metaobject_update = result['data']['metaobjectUpdate']
            if metaobject_update.get('userErrors'):
                logger.error(f"Failed to update partner store {store.id} with kiosk. User errors: {metaobject_update['userErrors']}")
            else:
                logger.info(f"Updated partner store {store.id} with kiosk {kiosk.id}")
                store.kiosks.add(kiosk)
        else:
            logger.error(f"Failed to update partner store {store.id} with kiosk: {result}")

    def extract_id_from_gid(self, gid):
        match = re.search(r'/([^/]+)$', gid)
        extracted_id = match.group(1) if match else gid
        logger.info(f"Extracted ID from GID: {gid} -> {extracted_id}")
        return extracted_id

    def update_store_owner_customer_record(self, kiosk, manager):
        store_owner = kiosk.store.owner
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

        current_kiosks = list(store_owner.associated_kiosks.values_list('shopify_id', flat=True))
        current_kiosks.append(kiosk.shopify_id)

        variables = {
            "input": {
                "id": store_owner.shopify_customer_id,
                "metafields": [
                    {
                        "namespace": "custom",
                        "key": "associated_kiosks",
                        "value": json.dumps(current_kiosks),
                        "type": "json"
                    }
                ]
            }
        }

        result = manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'customerUpdate' in result['data']:
            logger.info(f"Updated store owner {store_owner.id} with kiosk {kiosk.id}")
            store_owner.associated_kiosks.add(kiosk)
        else:
            logger.error(f"Failed to update store owner {store_owner.id} with kiosk: {result}")