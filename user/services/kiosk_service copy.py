# In user/services/kiosk_service.py

import logging
import json
import re
from urllib.parse import quote
from django.conf import settings
from user.models import PartnerStore, Kiosk, Product, KioskQRCode, Collection
from .shopify_connection import ShopifyConnectionManager
from .get_content_url import get_shopify_video_url, get_shopify_thumbnail_url, generate_qr_code_filename, predict_qr_code_url
from .upload_file import upload_file_to_shopify
from .qrcode import generate_qr_code, get_qr_code_url
logger = logging.getLogger(__name__)

class KioskService:
    def __init__(self, store_id):
        self.store = PartnerStore.objects.get(id=store_id)
        self.manager = ShopifyConnectionManager()

    def create_and_setup_kiosk(self):
        try:
            with self.manager:
                kiosk = self._create_kiosk_in_shopify()
                if kiosk:
                    self._associate_products_with_kiosk(kiosk)
                    collection_id = self._create_collection_for_kiosk(kiosk)
                    if collection_id:
                        self._update_kiosk_with_collection(kiosk, collection_id)
                    self._update_kiosk_metafields(kiosk)
                    self._update_product_metafields(kiosk)
                    self._update_partner_store(kiosk)
                    self._update_store_owner_customer_record(kiosk)
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



    def _associate_products_with_kiosk(self, kiosk):
        try:
            logger.info(f"Associating products with kiosk: {kiosk.name} (ID: {kiosk.id})")
            product_ids = []
            for product in Product.objects.all():
                logger.debug(f"Processing product: {product.shopify_id}")
                shopify_product = self._fetch_product_details_from_shopify(product.shopify_id)
                
                if shopify_product:
                    product.title = shopify_product.get('title', '')
                    product.price = shopify_product.get('price', 0.00)
                    product.description = shopify_product.get('description', '')
                    product.video_url = get_shopify_video_url(product.shopify_id)
                    product.thumbnail_url = get_shopify_thumbnail_url(product.shopify_id)
                    product.save()
                    
                    kiosk.products.add(product)
                    product_ids.append(product.shopify_id)
                    
                    qr_code_url = get_qr_code_url(kiosk.shopify_id, product.shopify_id)
                    qr_code_image = generate_qr_code(qr_code_url)
                    
                    filename = generate_qr_code_filename(kiosk.id, product.id)
                    file_id = upload_file_to_shopify(qr_code_image.getvalue(), filename, "image/png", product.shopify_id, self.manager)
                    
                    if file_id:
                        image_url = predict_qr_code_url(filename)
                        KioskQRCode.objects.update_or_create(
                            kiosk=kiosk,
                            product=product,
                            defaults={
                                'qr_code_url': qr_code_url,
                                'image_url': image_url,
                                'shopify_id': file_id
                            }
                        )
                        logger.debug(f"QR code uploaded and associated for product: {product.shopify_id}")
                    else:
                        logger.warning(f"Failed to upload QR code image for product {product.shopify_id}")
                else:
                    logger.warning(f"Failed to fetch details for product {product.shopify_id}")
            
            self._update_kiosk_products_in_shopify(kiosk, product_ids)
            
            logger.info(f"Associated {len(product_ids)} products with kiosk {kiosk.name}")
        except Exception as e:
            logger.error(f"Error associating products with kiosk: {str(e)}", exc_info=True)

    def _update_kiosk_metafields(self, kiosk):
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

        kiosk_qr_code_url = get_qr_code_url(kiosk.shopify_id, "main")
        product_ids = [self.ensure_shopify_gid(p.shopify_id, "Product") for p in kiosk.products.all()]
        qr_code_ids = [self.ensure_shopify_gid(qr.shopify_id, "Metaobject") for qr in kiosk.kiosk_qr_codes.all()]

        variables = {
            "id": self.ensure_shopify_gid(kiosk.shopify_id, "Metaobject"),
            "metaobject": {
                "fields": [
                    {"key": "kiosk_qr_code_url", "value": kiosk_qr_code_url},
                    {"key": "Products", "value": json.dumps(product_ids)},
                    {"key": "Store", "value": json.dumps([self.ensure_shopify_gid(kiosk.store.shopify_id, "Metaobject")])},
                    {"key": "is_active", "value": "true"},
                    {"key": "QR Codes", "value": json.dumps(qr_code_ids)},
                ]
            }
        }

        result = self.manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'metaobjectUpdate' in result['data']:
            logger.info(f"Successfully updated kiosk metafields for kiosk {kiosk.id}")
        else:
            logger.error(f"Failed to update kiosk metafields for kiosk {kiosk.id}: {result}")
    def _update_kiosk_metafields(self, kiosk):
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

        kiosk_qr_code_url = get_qr_code_url(kiosk.id, "main")
        product_ids = [self.ensure_shopify_gid(p.shopify_id, "Product") for p in kiosk.products.all()]
        qr_code_ids = [self.ensure_shopify_gid(qr.shopify_id, "Metaobject") for qr in kiosk.kiosk_qr_codes.all()]

        variables = {
            "id": self.ensure_shopify_gid(kiosk.shopify_id, "Metaobject"),
            "metaobject": {
                "fields": [
                    {"key": "kiosk_qr_code_url", "value": kiosk_qr_code_url},
                    {"key": "Products", "value": json.dumps(product_ids)},
                    {"key": "Store", "value": json.dumps([self.ensure_shopify_gid(kiosk.store.shopify_id, "Metaobject")])},
                    {"key": "is_active", "value": "true"},
                    {"key": "QR Codes", "value": json.dumps(qr_code_ids)},
                ]
            }
        }

        result = self.manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'metaobjectUpdate' in result['data']:
            logger.info(f"Successfully updated kiosk metafields for kiosk {kiosk.id}")
        else:
            logger.error(f"Failed to update kiosk metafields for kiosk {kiosk.id}: {result}")

    def _update_kiosk_products_in_shopify(self, kiosk, product_ids):
        try:
            mutation = """
            mutation updateKiosk($id: ID!, $input: MetaobjectUpdateInput!) {
                metaobjectUpdate(id: $id, metaobject: $input) {
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
                "id": kiosk.shopify_id,
                "input": {
                    "fields": [
                        {
                            "key": "Products",
                            "value": json.dumps(product_ids)
                        }
                    ]
                }
            }
            
            result = self.manager.execute_graphql_query(mutation, variables)
            
            if result and 'data' in result and 'metaobjectUpdate' in result['data']:
                if 'metaobject' in result['data']['metaobjectUpdate']:
                    logger.info(f"Updated kiosk {kiosk.name} in Shopify with {len(product_ids)} products")
                else:
                    errors = result['data']['metaobjectUpdate'].get('userErrors', [])
                    logger.error(f"Failed to update kiosk in Shopify: {errors}")
            else:
                logger.error(f"Unexpected response from Shopify: {result}")

        except Exception as e:
            logger.error(f"Error updating kiosk products in Shopify: {str(e)}")

    def _fetch_product_details_from_shopify(self, product_id):
        query = """
        query getProduct($id: ID!) {
            product(id: $id) {
                title
                priceRange {
                    minVariantPrice {
                        amount
                    }
                }
                description
            }
        }
        """
        variables = {"id": product_id}
        
        result = self.manager.execute_graphql_query(query, variables)
        
        if result and 'data' in result and 'product' in result['data']:
            product = result['data']['product']
            return {
                'title': product['title'],
                'price': float(product['priceRange']['minVariantPrice']['amount']),
                'description': product['description'],
            }
        else:
            logger.error(f"Failed to fetch product details from Shopify: {result}")
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
        result = self.manager.execute_graphql_query(mutation, variables)
        logger.info(f"GraphQL result: {result}")
        
        if result and 'data' in result and 'metaobjectUpdate' in result['data']:
            metaobject_update = result['data']['metaobjectUpdate']
            if not metaobject_update.get('userErrors'):
                logger.info(f"Successfully updated kiosk {kiosk.id} with collection {collection_id}")
                
                collection_id_raw = self.extract_id_from_gid(collection_id)
                
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

    def _update_partner_store(self, kiosk):
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
        current_kiosks_result = self.manager.execute_graphql_query(current_kiosks_query, current_kiosks_variables)
        
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
        result = self.manager.execute_graphql_query(mutation, variables)
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

    def _update_store_owner_customer_record(self, kiosk):
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

        result = self.manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'customerUpdate' in result['data']:
            logger.info(f"Updated store owner {store_owner.id} with kiosk {kiosk.id}")
            store_owner.associated_kiosks.add(kiosk)
        else:
            logger.error(f"Failed to update store owner {store_owner.id} with kiosk: {result}")

    def ensure_shopify_gid(self, id_value, resource_type):
        if isinstance(id_value, str) and id_value.startswith('gid://shopify/'):
            logger.info(f"ID already in GID format: {id_value}")
            return id_value
        gid = f"gid://shopify/{resource_type}/{id_value}"
        logger.info(f"Converted ID to GID: {id_value} -> {gid}")
        return gid

    def extract_id_from_gid(self, gid):
        match = re.search(r'/([^/]+)$', gid)
        extracted_id = match.group(1) if match else gid
        logger.info(f"Extracted ID from GID: {gid} -> {extracted_id}")
        return extracted_id



    def _update_kiosk_metafields(self, kiosk):
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

        kiosk_qr_code_url = predict_qr_code_url(generate_qr_code_filename(kiosk.id, "main"))
        product_ids = [self.ensure_shopify_gid(p.shopify_id, "Product") for p in kiosk.products.all()]
        qr_code_ids = [self.ensure_shopify_gid(qr.shopify_id, "Metaobject") for qr in kiosk.kiosk_qr_codes.all()]

        variables = {
            "id": self.ensure_shopify_gid(kiosk.shopify_id, "Metaobject"),
            "metaobject": {
                "fields": [
                    {"key": "kiosk_qr_code_url", "value": kiosk_qr_code_url},
                    {"key": "Products", "value": json.dumps(product_ids)},
                    {"key": "Store", "value": json.dumps([self.ensure_shopify_gid(kiosk.store.shopify_id, "Metaobject")])},
                    {"key": "is_active", "value": "true"},
                    {"key": "QR Codes", "value": json.dumps(qr_code_ids)},
                ]
            }
        }

        result = self.manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'metaobjectUpdate' in result['data']:
            logger.info(f"Successfully updated kiosk metafields for kiosk {kiosk.id}")
        else:
            logger.error(f"Failed to update kiosk metafields for kiosk {kiosk.id}: {result}")

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
            video_url = get_shopify_video_url(product.shopify_id)
            thumbnail_url = get_shopify_thumbnail_url(product.shopify_id)
            qr_codes = [self.ensure_shopify_gid(qr.shopify_id, "Metaobject") for qr in product.qr_codes.all()]
            collections = [self.ensure_shopify_gid(c.shopify_id, "Collection") for c in product.collections.all()]

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
                    ]
                }
            }

            result = self.manager.execute_graphql_query(mutation, variables)
            if result and 'data' in result and 'productUpdate' in result['data']:
                logger.info(f"Successfully updated product metafields for product {product.id}")
            else:
                logger.error(f"Failed to update product metafields for product {product.id}: {result}")