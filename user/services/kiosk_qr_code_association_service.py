import logging
from user.models import Kiosk, Product
from .shopify_connection import ShopifyConnectionManager
from .qr_code_service import QRCodeService
from .qrcode import ensure_gid
import json

logger = logging.getLogger(__name__)

class KioskQRCodeAssociationService:
    def __init__(self, kiosk_id):
        self.kiosk = Kiosk.objects.get(id=kiosk_id)
        self.manager = ShopifyConnectionManager()
        self.qr_code_service = QRCodeService(kiosk_id)

    def create_and_associate_qr_codes(self):
        try:
            kiosk_qr_code_url, kiosk_qr_code_metaobject_id = self._create_kiosk_qr_code()
            if not kiosk_qr_code_url or not kiosk_qr_code_metaobject_id:
                logger.error(f"Failed to create kiosk QR code for kiosk {self.kiosk.id}")
                return

            product_qr_codes = self._create_product_qr_codes()
            self._update_kiosk_metaobject(kiosk_qr_code_metaobject_id, product_qr_codes)
            self._update_product_metaobjects(product_qr_codes)
            logger.info(f"Successfully created and associated QR codes for kiosk {self.kiosk.id}")
        except Exception as e:
            logger.error(f"Error creating and associating QR codes for kiosk {self.kiosk.id}: {str(e)}")


    def _create_kiosk_qr_code(self):
        qr_code_url, file_id = self.qr_code_service.generate_and_upload_qr_code("main")
        if not qr_code_url or not file_id:
            logger.error(f"Failed to generate and upload QR code for kiosk {self.kiosk.id}")
            return None, None
        
        # Get the first associated product
        first_product = self.kiosk.products.first()
        if not first_product:
            logger.error(f"No products associated with kiosk {self.kiosk.id}")
            return None, None
        
        metaobject_id = self._create_qr_code_metaobject(first_product, qr_code_url, file_id)
        return qr_code_url, metaobject_id

    def _create_product_qr_codes(self):
        product_qr_codes = {}
        for product in self.kiosk.products.all():
            qr_code_url, file_id = self.qr_code_service.generate_and_upload_qr_code(product.id)
            if qr_code_url and file_id:
                qr_code_metaobject = self._create_qr_code_metaobject(product, qr_code_url, file_id)
                if qr_code_metaobject:
                    product_qr_codes[product.id] = qr_code_metaobject
            else:
                logger.error(f"Failed to generate and upload QR code for product {product.id}")
        return product_qr_codes


    def _create_qr_code_metaobject(self, product, qr_code_url, file_id):
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
            {"key": "qr_code_image", "value": file_id},
            {"key": "kiosk", "value": ensure_gid(self.kiosk.shopify_id, "Metaobject")},
        ]

        if product:
            fields.append({"key": "product", "value": ensure_gid(product.shopify_id, "Product")})

        variables = {
            "metaobject": {
                "type": "kiosk_qr_code",
                "fields": fields
            }
        }

        result = self.manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'metaobjectCreate' in result['data']:
            metaobject = result['data']['metaobjectCreate']['metaobject']
            if metaobject and 'id' in metaobject:
                return metaobject['id']
            else:
                user_errors = result['data']['metaobjectCreate'].get('userErrors', [])
                for error in user_errors:
                    logger.error(f"Error creating QR code metaobject: {error['message']}")
        else:
            logger.error(f"Unexpected response structure from Shopify API: {result}")
        
        logger.error(f"Failed to create QR code metaobject. Full result: {result}")
        return None

    def _update_kiosk_metaobject(self, kiosk_qr_code, product_qr_codes):
        mutation = """
        mutation updateKiosk($id: ID!, $metaobject: MetaobjectUpdateInput!) {
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

        # Combine kiosk QR code with product QR codes
        all_qr_codes = [kiosk_qr_code] + list(product_qr_codes.values())

        # Fetch the actual URL for the kiosk QR code
        kiosk_qr_code_url = self._get_qr_code_url(kiosk_qr_code)

        variables = {
            "id": ensure_gid(self.kiosk.shopify_id, "Metaobject"),
            "metaobject": {
                "fields": [
                    {"key": "kiosk_qr_code_url", "value": kiosk_qr_code_url},
                    {"key": "qr_codes", "value": json.dumps(all_qr_codes)},
                    {"key": "products", "value": json.dumps([ensure_gid(p.shopify_id, "Product") for p in self.kiosk.products.all()])},
                    {"key": "is_active", "value": "true"},
                ]
            }
        }

        result = self.manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'metaobjectUpdate' in result['data']:
            updated_metaobject = result['data']['metaobjectUpdate']['metaobject']
            if updated_metaobject:
                logger.info(f"Successfully updated kiosk metaobject. Fields: {updated_metaobject['fields']}")
            else:
                user_errors = result['data']['metaobjectUpdate'].get('userErrors', [])
                for error in user_errors:
                    logger.error(f"Error updating kiosk metaobject: {error['message']}")
        else:
            logger.error(f"Failed to update kiosk metaobject: {result}")

    def _get_qr_code_url(self, qr_code_metaobject_id):
        query = """
        query getQRCodeURL($id: ID!) {
            metaobject(id: $id) {
                fields {
                    key
                    value
                }
            }
        }
        """
        variables = {
            "id": qr_code_metaobject_id
        }
        result = self.manager.execute_graphql_query(query, variables)
        if result and 'data' in result and 'metaobject' in result['data']:
            fields = result['data']['metaobject']['fields']
            for field in fields:
                if field['key'] == 'qr_code_url':
                    return field['value']
        logger.error(f"Failed to fetch QR code URL for metaobject: {qr_code_metaobject_id}")
        return None

    def _update_product_metaobjects(self, product_qr_codes):
        # Get all QR codes for the kiosk
        all_qr_codes = list(product_qr_codes.values())

        for product in self.kiosk.products.all():
            mutation = """
            mutation updateProduct($input: ProductInput!) {
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
                    "id": ensure_gid(product.shopify_id, "Product"),
                    "metafields": [
                        {
                            "namespace": "custom",
                            "key": "kiosk_qr_codes",
                            "value": json.dumps(all_qr_codes),
                            "type": "list.metaobject_reference"
                        }
                    ]
                }
            }

            result = self.manager.execute_graphql_query(mutation, variables)
            if not (result and 'data' in result and 'productUpdate' in result['data']):
                logger.error(f"Failed to update product metaobject for product {product.id}: {result}")
            else:
                logger.info(f"Successfully updated product metaobject for product {product.id}")