import logging
from django.conf import settings
from user.models import PartnerStore, Kiosk, Product, Collection
from .shopify_connection import ShopifyConnectionManager
from .kiosk_association_service import KioskAssociationService
import json

logger = logging.getLogger(__name__)

class KioskService:
    def __init__(self, store_id):
        self.store = PartnerStore.objects.get(id=store_id)
        self.manager = ShopifyConnectionManager()
        self.association_service = KioskAssociationService(store_id)

   

    def create_and_setup_kiosk(self):
        try:
            with self.manager:
                kiosk = self._create_kiosk_in_shopify()
                if kiosk:
                    collection_id = self._create_collection_for_kiosk(kiosk)
                    if collection_id:
                        self._update_kiosk_with_collection(kiosk, collection_id)
                    self.association_service.update_associations(kiosk)
                    return kiosk
        except Exception as e:
            logger.error(f"Error in create_and_setup_kiosk: {str(e)}", exc_info=True)
        return None

    def _create_kiosk_in_shopify(self):
        try:
            logger.debug("Fetching metaobject definitions from Shopify")
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
            
            result = self.manager.execute_graphql_query(query)
            logger.debug(f"Metaobject definitions result: {result}")
            
            if result is None or 'data' not in result or 'metaobjectDefinitions' not in result['data']:
                logger.error(f"Failed to fetch metaobject definitions: {result}")
                return None
            
            kiosk_definition = next((node['node'] for node in result['data']['metaobjectDefinitions']['edges'] if node['node']['type'] == 'kiosk'), None)
            
            if not kiosk_definition:
                logger.error("Kiosk metaobject definition not found")
                return None
            
            field_keys = {fd['name'].lower(): {'key': fd['key'], 'type': fd['type']['name']} for fd in kiosk_definition['fieldDefinitions']}
            
            mutation = """
            mutation createKiosk($input: MetaobjectCreateInput!) {
                metaobjectCreate(metaobject: $input) {
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
            
            fields = [
                {"key": field_keys['name']['key'], "value": f"Kiosk for {self.store.name}"},
                {"key": field_keys['is_active']['key'], "value": "true"}
            ]
            
            if 'store' in field_keys and field_keys['store']['type'] == 'list.metaobject_reference':
                fields.append({"key": field_keys['store']['key'], "value": json.dumps([self.store.shopify_id])})
            
            variables = {
                "input": {
                    "type": "kiosk",
                    "fields": fields
                }
            }

            logger.debug(f"Creating kiosk with fields: {fields}")
            result = self.manager.execute_graphql_query(mutation, variables)
            logger.debug(f"Create kiosk result: {result}")

            if result and 'data' in result and 'metaobjectCreate' in result['data']:
                metaobject_create = result['data']['metaobjectCreate']
                if metaobject_create['metaobject']:
                    shopify_kiosk_id = metaobject_create['metaobject']['id']
                    kiosk = Kiosk.objects.create(
                        shopify_id=shopify_kiosk_id,
                        name=f"Kiosk for {self.store.name}",
                        store=self.store,
                        is_active=True
                    )
                    logger.info(f"Created kiosk in Shopify and Django: {kiosk.name} (ID: {kiosk.id})")
                    return kiosk
                else:
                    errors = metaobject_create.get('userErrors', [])
                    logger.error(f"Failed to create kiosk in Shopify: {errors}")
            else:
                logger.error(f"Unexpected response structure from Shopify: {result}")

        except Exception as e:
            logger.error(f"Error creating kiosk in Shopify: {str(e)}", exc_info=True)
        return None

    def _create_collection_for_kiosk(self, kiosk):
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

        result = self.manager.execute_graphql_query(mutation, variables)
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

    def _update_kiosk_with_collection(self, kiosk, collection_id):
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
        kiosk_gid = self.association_service.ensure_shopify_gid(kiosk.shopify_id, "Metaobject")
        collection_gid = self.association_service.ensure_shopify_gid(collection_id, "Collection")
        
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
        result = self.manager.execute_graphql_query(mutation, variables)
        logger.info(f"GraphQL result: {result}")
        
        if result and 'data' in result and 'metaobjectUpdate' in result['data']:
            metaobject_update = result['data']['metaobjectUpdate']
            if not metaobject_update.get('userErrors'):
                logger.info(f"Successfully updated kiosk {kiosk.id} with collection {collection_id}")
                
                collection_id_raw = self.association_service.extract_id_from_gid(collection_id)
                
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
                
                kiosk.collection = collection
                kiosk.save()
                logger.info(f"Updated kiosk {kiosk.id} with collection {collection.id}")
            else:
                logger.error(f"Failed to update kiosk. Error: {metaobject_update['userErrors']}")
        else:
            logger.error(f"Failed to update kiosk {kiosk.id} with collection: {result}")