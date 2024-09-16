from django.db.models.signals import post_save
from django.dispatch import receiver
from user.models import MerchantStore
import logging 
from user.services.shopify_metadata_manager import ShopifyMetadataManager
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=MerchantStore)
def create_shopify_metaobject(sender, instance, created, **kwargs):
    if created:
        shopify_manager = ShopifyMetadataManager()
        try:
            result = shopify_manager.create_merchant_store_metaobject(
                merchant_id=instance.merchant.id,
                store_name=instance.store_name,
                address=instance.address,
                is_active=instance.is_active
            )
            logger.info(f"Shopify metaobject creation result: {result}")
            if not result:
                logger.error("Metaobject creation failed without raising an exception")
        except Exception as e:
            logger.error(f"Error creating Shopify metaobject: {str(e)}", exc_info=True)