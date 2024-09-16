import logging
from user.models import Kiosk, Product
from .shopify_connection import ShopifyConnectionManager
from .qrcode import ensure_gid
import json

logger = logging.getLogger(__name__)

class ProductQRCodeAssociationService:
    def __init__(self, kiosk_id):
        self.kiosk = Kiosk.objects.get(id=kiosk_id)
        self.manager = ShopifyConnectionManager()

    def associate_qr_codes_to_products(self):
        try:
            kiosk_qr_codes = self._get_kiosk_qr_codes()
            self._update_product_metafields(kiosk_qr_codes)
            logger.info(f"Successfully associated QR codes to products for kiosk {self.kiosk.id}")
        except Exception as e:
            logger.error(f"Error associating QR codes to products for kiosk {self.kiosk.id}: {str(e)}")

    def _get_kiosk_qr_codes(self):
        query = """
        query getKioskQRCodes($id: ID!) {
            metaobject(id: $id) {
                fields {
                    key
                    value
                }
            }
        }
        """
        variables = {
            "id": ensure_gid(self.kiosk.shopify_id, "Metaobject")
        }
        result = self.manager.execute_graphql_query(query, variables)
        if result and 'data' in result and 'metaobject' in result['data']:
            fields = result['data']['metaobject']['fields']
            for field in fields:
                if field['key'] == 'qr_codes':
                    return json.loads(field['value'])
        logger.error(f"Failed to fetch QR codes for kiosk: {self.kiosk.id}")
        return []

    def _update_product_metafields(self, kiosk_qr_codes):
        for product in self.kiosk.products.all():
            self._update_single_product_metafield(product, kiosk_qr_codes)

    def _update_single_product_metafield(self, product, kiosk_qr_codes):
        mutation = """
        mutation updateProductMetafields($input: ProductInput!) {
            productUpdate(input: $input) {
                product {
                    id
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
                        "namespace": "app--146637160449",
                        "key": "kiosk_ids",
                        "value": json.dumps([self.kiosk.shopify_id]),
                        "type": "list.single_line_text_field"
                    },
                    {
                        "namespace": "custom",
                        "key": "kiosk_qr_codes",
                        "value": json.dumps(kiosk_qr_codes),
                        "type": "list.metaobject_reference"
                    }
                ]
            }
        }

        result = self.manager.execute_graphql_query(mutation, variables)
        if result and 'data' in result and 'productUpdate' in result['data']:
            product_data = result['data']['productUpdate']['product']
            if product_data:
                metafields = product_data['metafields']['edges']
                kiosk_qr_codes_set = False
                for metafield in metafields:
                    if metafield['node']['namespace'] == 'custom' and metafield['node']['key'] == 'kiosk_qr_codes':
                        kiosk_qr_codes_set = True
                        break
                if kiosk_qr_codes_set:
                    logger.info(f"Successfully updated product metafields for product {product.id}")
                else:
                    logger.warning(f"kiosk_qr_codes metafield not found after update for product {product.id}")
            else:
                logger.error(f"No product data returned after update for product {product.id}")
        else:
            logger.error(f"Failed to update product metafields for product {product.id}: {result}")