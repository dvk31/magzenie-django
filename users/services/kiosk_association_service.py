import logging
import json
from django.conf import settings
from user.models import PartnerStore, Kiosk, Product, Collection
from .shopify_connection import ShopifyConnectionManager
from .qrcode import ensure_gid
import re

logger = logging.getLogger(__name__)

class KioskAssociationService:
    def __init__(self, store_id):
        self.store = PartnerStore.objects.get(id=store_id)
        self.manager = ShopifyConnectionManager()

    def ensure_shopify_gid(self, id_value, resource_type):
        return ensure_gid(id_value, resource_type)

    @staticmethod
    def extract_id_from_gid(gid):
        match = re.search(r'/([^/]+)$', gid)
        extracted_id = match.group(1) if match else gid
        return extracted_id

    def update_associations(self, kiosk):
        try:
            with self.manager:
                self._update_kiosk_metafields(kiosk)
                self._update_product_metafields(kiosk)
                self._update_collection_metafields(kiosk)
                self._update_store_owner_metafields(kiosk)
            logger.info(f"Successfully updated all associations for kiosk {kiosk.id}")
        except Exception as e:
            logger.error(f"Error updating associations for kiosk {kiosk.id}: {str(e)}", exc_info=True)

    def _update_kiosk_metafields(self, kiosk):
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

        product_ids = [self.ensure_shopify_gid(p.shopify_id, "Product") for p in kiosk.products.all()]

        variables = {
            "id": self.ensure_shopify_gid(kiosk.shopify_id, "Metaobject"),
            "metaobject": {
                "fields": [
                    {"key": "name", "value": kiosk.name},
                    {"key": "products", "value": json.dumps(product_ids)},
                    {"key": "store", "value": json.dumps([self.ensure_shopify_gid(kiosk.store.shopify_id, "Metaobject")])},
                    {"key": "is_active", "value": "true"},
                    {"key": "collection", "value": self.ensure_shopify_gid(kiosk.collection.shopify_id, "Collection") if kiosk.collection else None},
                ]
            }
        }

        result = self.manager.execute_graphql_query(mutation, variables)
        self._handle_graphql_result(result, "kiosk metafields", kiosk.id)

    def _update_product_metafields(self, kiosk):
        for product in kiosk.products.all():
            mutation = """
            mutation productUpdate($input: ProductInput!) {
                productUpdate(input: $input) {
                    product {
                        id
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """

            kiosk_ids = [self.ensure_shopify_gid(k.shopify_id, "Metaobject") for k in product.kiosks.all()]
            video_url = self.get_shopify_video_url(product.shopify_id)
            thumbnail_url = self.get_shopify_thumbnail_url(product.shopify_id)
            collections = [self.ensure_shopify_gid(c.shopify_id, "Collection") for c in product.collections.all()]

            variables = {
                "input": {
                    "id": self.ensure_shopify_gid(product.shopify_id, "Product"),
                    "metafields": [
                        {"namespace": "app--146637160449", "key": "kiosk_ids", "value": json.dumps(kiosk_ids), "type": "list.single_line_text_field"},
                        {"namespace": "custom", "key": "video_url", "value": video_url, "type": "url"},
                        {"namespace": "custom", "key": "thumbnail_url", "value": thumbnail_url, "type": "url"},
                        {"namespace": "custom", "key": "kiosk_collections", "value": json.dumps(collections), "type": "list.collection_reference"},
                        {"namespace": "custom", "key": "kiosk_active", "value": "true", "type": "boolean"},
                    ]
                }
            }

            result = self.manager.execute_graphql_query(mutation, variables)
            self._handle_graphql_result(result, "product metafields", product.id)

    def _update_collection_metafields(self, kiosk):
        collection = kiosk.collection
        if not collection:
            logger.warning(f"No collection associated with kiosk {kiosk.id}")
            return

        mutation = """
        mutation collectionUpdate($input: CollectionInput!) {
            collectionUpdate(input: $input) {
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

        metafields = [
            {"namespace": "custom", "key": "kiosk_sort_order", "value": str(getattr(kiosk, 'sort_order', 0)), "type": "number_integer"},
            {"namespace": "custom", "key": "_kiosk_display_name", "value": kiosk.name, "type": "single_line_text_field"},
            {"namespace": "custom", "key": "kiosk_description", "value": getattr(kiosk, 'description', '') or "", "type": "multi_line_text_field"},
            {"namespace": "custom", "key": "kiosk_active", "value": "true", "type": "boolean"},
        ]

        if hasattr(kiosk, 'display_start_date') and kiosk.display_start_date:
            metafields.append({
                "namespace": "custom",
                "key": "kiosk_display_start_date",
                "value": kiosk.display_start_date.isoformat(),
                "type": "date_time"
            })

        variables = {
            "input": {
                "id": self.ensure_shopify_gid(collection.shopify_id, "Collection"),
                "metafields": metafields
            }
        }

        result = self.manager.execute_graphql_query(mutation, variables)
        self._handle_graphql_result(result, "collection metafields", kiosk.id)

    def _update_store_owner_metafields(self, kiosk):
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
        if kiosk.shopify_id not in current_kiosks:
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

        result = self.manager.execute_graphql_query(mutation, variables)
        if self._handle_graphql_result(result, "store owner metafields", store_owner.id):
            store_owner.associated_kiosks.add(kiosk)

    def _handle_graphql_result(self, result, operation, entity_id):
        if result and 'data' in result:
            operation_key = next(iter(result['data']))
            if operation_key in result['data']:
                logger.info(f"Successfully updated {operation} for {entity_id}")
                return True
        logger.error(f"Failed to update {operation} for {entity_id}: {result}")
        return False

    def _log_kiosk_metaobject_state(self, kiosk):
        query = """
        query getKioskMetaobject($id: ID!) {
            metaobject(id: $id) {
                id
                type
                fields {
                    key
                    value
                }
            }
        }
        """
        variables = {"id": self.ensure_shopify_gid(kiosk.shopify_id, "Metaobject")}
        result = self.manager.execute_graphql_query(query, variables)
        if result and 'data' in result and 'metaobject' in result['data']:
            logger.info(f"Current state of kiosk metaobject: {json.dumps(result['data']['metaobject'], indent=2)}")
        else:
            logger.error(f"Failed to fetch current state of kiosk metaobject: {json.dumps(result, indent=2)}")

    def get_shopify_video_url(self, product_id):
        query = """
        query getProductVideoGid($id: ID!) {
          product(id: $id) {
            metafields(first: 10) {
              edges {
                node {
                  namespace
                  key
                  value
                }
              }
            }
          }
        }
        """
        variables = {"id": product_id}
        
        result = self.manager.execute_graphql_query(query, variables)
        
        video_gid = None
        if result and 'data' in result:
            metafields = result['data']['product']['metafields']['edges']
            for metafield in metafields:
                node = metafield['node']
                if node['key'] == 'kiosk_video':
                    video_gid = node['value']
                    break
        
        if not video_gid:
            return None
        
        video_query = """
        query getVideoUrl($id: ID!) {
          node(id: $id) {
            ... on Video {
              sources {
                url
              }
            }
          }
        }
        """
        video_variables = {"id": video_gid}
        
        video_result = self.manager.execute_graphql_query(video_query, video_variables)
        
        if video_result and 'data' in video_result:
            node = video_result['data'].get('node')
            if node and 'sources' in node:
                sources = node['sources']
                if sources:
                    return sources[0]['url']
        
        return None

    def get_shopify_thumbnail_url(self, product_id):
        query = """
        query getProductThumbnail($id: ID!) {
          product(id: $id) {
            featuredImage {
              url
            }
          }
        }
        """
        variables = {"id": product_id}
        
        result = self.manager.execute_graphql_query(query, variables)
        
        if result and 'data' in result:
            product = result['data']['product']
            if product and product['featuredImage']:
                return product['featuredImage']['url']
        
        logger.error(f"Failed to retrieve thumbnail URL for product ID: {product_id}")
        return None