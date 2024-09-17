import logging
import json
import uuid
from django.conf import settings
from user.models import PartnerStore, Kiosk, Product, KioskQRCode, Collection
from .shopify_connection import ShopifyConnectionManager
from .upload_file import upload_file_to_shopify
from .qr_code_service import QRCodeService
from .qrcode import ensure_gid
from .get_content_url import get_qr_code_image_url
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
                self._generate_and_upload_qr_codes(kiosk)
                self._update_product_metafields(kiosk)
                self._update_collection_metafields(kiosk)
                self._update_store_owner_metafields(kiosk)
            logger.info(f"Successfully updated all associations for kiosk {kiosk.id}")
        except Exception as e:
            logger.error(f"Error updating associations for kiosk {kiosk.id}: {str(e)}", exc_info=True)

    def _generate_and_upload_qr_codes(self, kiosk):
        qr_code_service = QRCodeService(kiosk.id)
        all_qr_code_metaobjects = []

        # Generate and upload main kiosk QR code if it doesn't exist
        if not kiosk.qr_code_url:
            main_qr_code_url = qr_code_service.generate_and_upload_qr_code("main")
            if main_qr_code_url:
                main_qr_code_metaobject = self._create_qr_code_metaobject(kiosk, None, main_qr_code_url, "main")
                if main_qr_code_metaobject:
                    all_qr_code_metaobjects.append(main_qr_code_metaobject)
                    self._update_kiosk_qr_code(kiosk, main_qr_code_url, main_qr_code_metaobject)

        # Generate and upload QR codes for each product in the kiosk
        for product in kiosk.products.all():
            existing_qr_code = KioskQRCode.objects.filter(kiosk=kiosk, product=product).first()
            if not existing_qr_code:
                product_qr_code_url = qr_code_service.generate_and_upload_qr_code(product.id)
                if product_qr_code_url:
                    qr_code_metaobject = self._create_qr_code_metaobject(kiosk, product, product_qr_code_url, "product")
                    if qr_code_metaobject:
                        all_qr_code_metaobjects.append(qr_code_metaobject)
                        self._update_product_qr_code(product, product_qr_code_url, qr_code_metaobject)

        # Update kiosk with all QR code metaobjects
        if all_qr_code_metaobjects:
            self._update_kiosk_with_qr_codes(kiosk, all_qr_code_metaobjects)

        logger.info(f"Generated and uploaded QR codes for kiosk {kiosk.id}: {len(all_qr_code_metaobjects)} new QR codes")

    def _update_kiosk_with_qr_codes(self, kiosk, qr_code_metaobjects):
        mutation = """
        mutation updateKioskQRCodes($id: ID!, $metaobject: MetaobjectUpdateInput!) {
            metaobjectUpdate(id: $id, metaobject: $metaobject) {
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
            "id": self.ensure_shopify_gid(kiosk.shopify_id, "Metaobject"),
            "metaobject": {
                "fields": [
                    {"key": "qr_codes", "value": json.dumps(qr_code_metaobjects)}
                ]
            }
        }

        result = self.manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'metaobjectUpdate' in result['data']:
            logger.info(f"Successfully updated kiosk {kiosk.id} with QR code metaobjects")
        else:
            logger.error(f"Failed to update kiosk {kiosk.id} with QR code metaobjects: {result}")



    def _create_qr_code_metaobject(self, kiosk, product, qr_code_url, qr_code_type="product"):
        mutation = """
        mutation createQRCodeMetaobject($metaobject: MetaobjectCreateInput!) {
            metaobjectCreate(metaobject: $metaobject) {
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
        
        fields = [
            {"key": "qr_code_url", "value": qr_code_url},
            {"key": "kiosk", "value": self.ensure_shopify_gid(kiosk.shopify_id, "Metaobject")},
        ]

        if qr_code_type != "main" and product:
            fields.append({"key": "product", "value": self.ensure_shopify_gid(product.shopify_id, "Product")})

        variables = {
            "metaobject": {
                "type": "kiosk_qr_code",
                "fields": fields
            }
        }

        result = self.manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'metaobjectCreate' in result['data']:
            metaobject_create = result['data']['metaobjectCreate']
            if 'userErrors' in metaobject_create and metaobject_create['userErrors']:
                logger.error(f"Errors creating QR code metaobject: {json.dumps(metaobject_create['userErrors'], indent=2)}")
                return None
            return metaobject_create['metaobject']['id']
        else:
            logger.error(f"Failed to create QR code metaobject: {result}")
            return None




    def _update_kiosk_qr_code(self, kiosk, qr_code_url, qr_code_metaobject=None):
        mutation = """
        mutation metaobjectUpdate($id: ID!, $metaobject: MetaobjectUpdateInput!) {
            metaobjectUpdate(id: $id, metaobject: $metaobject) {
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
        fields = [
            {"key": "kiosk_qr_code_url", "value": qr_code_url}
        ]
        
        if qr_code_metaobject:
            fields.append({"key": "qr_codes", "value": json.dumps([qr_code_metaobject])})
        
        variables = {
            "id": self.ensure_shopify_gid(kiosk.shopify_id, "Metaobject"),
            "metaobject": {
                "fields": fields
            }
        }
        
        result = self.manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'metaobjectUpdate' in result['data']:
            logger.info(f"Successfully updated kiosk {kiosk.id} with QR code URL" + 
                        (" and metaobject" if qr_code_metaobject else ""))
        else:
            logger.error(f"Failed to update kiosk {kiosk.id} with QR code URL" + 
                        (" and metaobject" if qr_code_metaobject else "") + f": {result}")

    def _update_kiosk_qr_code(self, kiosk, qr_code_url, qr_code_metaobject=None):
        mutation = """
        mutation metaobjectUpdate($id: ID!, $metaobject: MetaobjectUpdateInput!) {
            metaobjectUpdate(id: $id, metaobject: $metaobject) {
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
        fields = [
            {"key": "kiosk_qr_code_url", "value": qr_code_url}
        ]
        
        if qr_code_metaobject:
            fields.append({"key": "qr_codes", "value": json.dumps([qr_code_metaobject])})
        
        variables = {
            "id": self.ensure_shopify_gid(kiosk.shopify_id, "Metaobject"),
            "metaobject": {
                "fields": fields
            }
        }
        
        result = self.manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'metaobjectUpdate' in result['data']:
            logger.info(f"Successfully updated kiosk {kiosk.id} with QR code URL" + 
                        (" and metaobject" if qr_code_metaobject else ""))
        else:
            logger.error(f"Failed to update kiosk {kiosk.id} with QR code URL" + 
                        (" and metaobject" if qr_code_metaobject else "") + f": {result}")




    def _update_product_qr_code(self, product, qr_code_url, qr_code_metaobject):
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
        variables = {
            "input": {
                "id": self.ensure_shopify_gid(product.shopify_id, "Product"),
                "metafields": [
                    {
                        "namespace": "custom",
                        "key": "qr_code_url",
                        "value": qr_code_url,
                        "type": "url"
                    },
                    {
                        "namespace": "custom",
                        "key": "qr_code_metaobject",
                        "value": qr_code_metaobject,
                        "type": "metaobject_reference"
                    }
                ]
            }
        }
        result = self.manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'productUpdate' in result['data']:
            logger.info(f"Successfully updated product {product.id} with QR code URL and metaobject")
        else:
            logger.error(f"Failed to update product {product.id} with QR code URL and metaobject: {result}")

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

        qr_code_service = QRCodeService(kiosk.id)
        kiosk_qr_code_url = get_qr_code_image_url(kiosk.id, "main")
        product_ids = [self.ensure_shopify_gid(p.shopify_id, "Product") for p in kiosk.products.all()]
        qr_code_ids = [self.ensure_shopify_gid(qr.shopify_id, "Metaobject") for qr in kiosk.kiosk_qr_codes.all() if qr.shopify_id]

        variables = {
            "id": self.ensure_shopify_gid(kiosk.shopify_id, "Metaobject"),
            "metaobject": {
                "fields": [
                    {"key": "name", "value": kiosk.name},
                    {"key": "kiosk_qr_code_url", "value": kiosk_qr_code_url},
                    {"key": "products", "value": json.dumps(product_ids)},
                    {"key": "store", "value": json.dumps([self.ensure_shopify_gid(kiosk.store.shopify_id, "Metaobject")])},
                    {"key": "is_active", "value": "true"},
                    {"key": "collection", "value": self.ensure_shopify_gid(kiosk.collection.shopify_id, "Collection") if kiosk.collection else None},
                ]
            }
        }

        if qr_code_ids:
            variables["metaobject"]["fields"].append({"key": "qr_codes", "value": json.dumps(qr_code_ids)})

        logger.debug(f"Updating kiosk metafields with variables: {json.dumps(variables, indent=2)}")

        result = self.manager.execute_graphql_query(mutation, variables)
        if result is None:
            logger.error("GraphQL query returned None. Check the ShopifyConnectionManager for errors.")
            return

        if 'data' in result and 'metaobjectUpdate' in result['data']:
            metaobject_update = result['data']['metaobjectUpdate']
            if 'userErrors' in metaobject_update and metaobject_update['userErrors']:
                logger.error(f"Errors updating kiosk metafields: {json.dumps(metaobject_update['userErrors'], indent=2)}")
                for error in metaobject_update['userErrors']:
                    logger.error(f"Error in field {error['field']}: {error['message']}")
            else:
                logger.info(f"Successfully updated kiosk metafields for kiosk {kiosk.id}")
                logger.debug(f"Updated product IDs: {product_ids}")
                logger.debug(f"Metaobject update result: {json.dumps(metaobject_update, indent=2)}")

                updated_fields = metaobject_update['metaobject']['fields']
                product_field = next((field for field in updated_fields if field['key'] == 'products'), None)
                if product_field:
                    logger.info(f"Products updated successfully: {product_field['value']}")
                else:
                    logger.warning("Products field not found in the updated metafields")
        else:
            logger.error(f"Unexpected response structure from Shopify: {json.dumps(result, indent=2)}")

        self._log_kiosk_metaobject_state(kiosk)

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

    def _update_product_metafields(self, kiosk):
        qr_code_service = QRCodeService(kiosk.id)
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
            qr_codes = [self.ensure_shopify_gid(qr.shopify_id, "Metaobject") for qr in product.qr_codes.all()]
            collections = [self.ensure_shopify_gid(c.shopify_id, "Collection") for c in product.collections.all()]

            qr_code_url = qr_code_service._get_qr_code_relative_url(product.id)

            variables = {
                "input": {
                    "id": self.ensure_shopify_gid(product.shopify_id, "Product"),
                    "metafields": [
                        {"namespace": "app--146637160449", "key": "kiosk_ids", "value": json.dumps(kiosk_ids), "type": "list.single_line_text_field"},
                        {"namespace": "custom", "key": "video_url", "value": video_url, "type": "url"},
                        {"namespace": "custom", "key": "thumbnail_url", "value": thumbnail_url, "type": "url"},
                        {"namespace": "custom", "key": "kiosk_qr_codes", "value": json.dumps(qr_codes), "type": "list.metaobject_reference"},
                        {"namespace": "custom", "key": "kiosk_collections", "value": json.dumps(collections), "type": "list.collection_reference"},
                        {"namespace": "custom", "key": "kiosk_active", "value": "true", "type": "boolean"},
                        {"namespace": "custom", "key": "qr_code_url", "value": qr_code_url, "type": "url"},
                    ]
                }
            }

            result = self.manager.execute_graphql_query(mutation, variables)
            if result and 'data' in result and 'productUpdate' in result['data']:
                logger.info(f"Successfully updated product metafields for product {product.id}")
            else:
                logger.error(f"Failed to update product metafields for product {product.id}: {result}")

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

        if hasattr(kiosk, 'image') and kiosk.image:
            image_id = self._upload_image_to_shopify(kiosk.image, kiosk.id)
            if image_id:
                variables["input"]["metafields"].append({
                    "namespace": "custom", 
                    "key": "kiosk_image", 
                    "value": image_id, 
                    "type": "file_reference"
                })

        result = self.manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'collectionUpdate' in result['data']:
            logger.info(f"Successfully updated collection metafields for kiosk {kiosk.id}")
        else:
            logger.error(f"Failed to update collection metafields for kiosk {kiosk.id}: {result}")

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
        if result and 'data' in result and 'customerUpdate' in result['data']:
            logger.info(f"Updated store owner {store_owner.id} with kiosk {kiosk.id}")
            store_owner.associated_kiosks.add(kiosk)
        else:
            logger.error(f"Failed to update store owner {store_owner.id} with kiosk: {result}")

    def _upload_image_to_shopify(self, image, kiosk_id):
        filename = f"kiosk_image_{kiosk_id}_{uuid.uuid4()}.png"
        file_content = image.read()
        file_type = "image/png"
        return upload_file_to_shopify(file_content, filename, file_type, kiosk_id, self.manager)

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
                if node['key'] == 'kiosk_video':  # Adjust this key to match your setup
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
                    return sources[0]['url']  # Assuming you want the first available source URL
        
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