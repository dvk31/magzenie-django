# user/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.apps import apps
from user.services.shopify_connection import ShopifyConnectionManager

import logging

logger = logging.getLogger(__name__)

def get_kiosk_qr_code_model():
    return apps.get_model('user', 'KioskQRCode')

@receiver(post_save, sender='user.KioskQRCode')
def kiosk_qr_code_post_save(sender, instance, created, **kwargs):
    action = 'create' if created else 'update'
    update_shopify_kiosk_qr_code(instance, action)

@receiver(post_delete, sender='user.KioskQRCode')
def kiosk_qr_code_post_delete(sender, instance, **kwargs):
    if instance.shopify_id:
        delete_shopify_kiosk_qr_code(instance.shopify_id)

def update_shopify_kiosk_qr_code(kiosk_qr_code, action):
    manager = ShopifyConnectionManager()
    
    mutation = """
    mutation metaobjectUpsert($metaobject: MetaobjectUpsertInput!) {
      metaobjectUpsert(metaobject: $metaobject) {
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
        "metaobject": {
            "type": "kiosk_qr_code",
            "id": kiosk_qr_code.shopify_id if action == 'update' else None,
            "fields": [
                {"key": "Product", "value": str(kiosk_qr_code.product.shopify_id)},
                {"key": "QR Code URL", "value": kiosk_qr_code.qr_code_url},
                {"key": "QR Code Image", "value": kiosk_qr_code.image_url},
                {"key": "kiosk", "value": str(kiosk_qr_code.kiosk.shopify_id)},
            ]
        }
    }
    
    result = manager.execute_graphql_query(mutation, variables)
    if result and 'data' in result and 'metaobjectUpsert' in result['data']:
        metaobject = result['data']['metaobjectUpsert']['metaobject']
        if metaobject and 'id' in metaobject:
            KioskQRCode = get_kiosk_qr_code_model()
            KioskQRCode.objects.filter(id=kiosk_qr_code.id).update(shopify_id=metaobject['id'])
            logger.info(f"KioskQRCode {action}d in Shopify: {kiosk_qr_code.id}")
        else:
            logger.error(f"Failed to {action} KioskQRCode in Shopify: {kiosk_qr_code.id}")
    else:
        logger.error(f"Error {action}ing KioskQRCode in Shopify: {kiosk_qr_code.id}")

def delete_shopify_kiosk_qr_code(shopify_id):
    manager = ShopifyConnectionManager()
    
    mutation = """
    mutation metaobjectDelete($id: ID!) {
      metaobjectDelete(id: $id) {
        deletedId
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {"id": shopify_id}
    
    result = manager.execute_graphql_query(mutation, variables)
    if result and 'data' in result and 'metaobjectDelete' in result['data']:
        deleted_id = result['data']['metaobjectDelete']['deletedId']
        if deleted_id:
            logger.info(f"KioskQRCode deleted from Shopify: {shopify_id}")
        else:
            logger.error(f"Failed to delete KioskQRCode from Shopify: {shopify_id}")
    else:
        logger.error(f"Error deleting KioskQRCode from Shopify: {shopify_id}")