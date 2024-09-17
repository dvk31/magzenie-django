import logging
from django.core.management.base import BaseCommand
from user.services.shopify_connection import ShopifyConnectionManager
import shopify
from pyactiveresource.connection import ResourceNotFound

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates Shopify webhook subscriptions and lists available topics'

    def handle(self, *args, **kwargs):
        with ShopifyConnectionManager() as manager:
            self.list_webhook_topics()
            self.update_webhook_subscriptions()

    def list_webhook_topics(self):
        logger.info("Listing available webhook topics...")
        available_topics = [
            "products/create",
            "products/update",
            "metaobjects/create",
            "metaobjects/update",
            "metaobjects/delete"
        ]
        for topic in available_topics:
            logger.info(f"Available topic: {topic}")

    def update_webhook_subscriptions(self):
        callback_url = "https://dev.withgpt.com/api/v1/webhooks/kiosk-qr-code"
        topic = "metaobjects/update"
        filter = "type:banana"

        try:
            # List existing webhooks for debugging
            existing_webhooks = shopify.Webhook.find()
            logger.info(f"Existing webhooks: {existing_webhooks}")

            webhook = shopify.Webhook.find_first(topic=topic)
            if webhook:
                webhook.address = callback_url
                webhook.save()
                logger.info(f"Updated webhook for topic {topic}")
            else:
                webhook = shopify.Webhook.create({
                    "topic": topic,
                    "address": callback_url,
                    "format": "json",
                    "filter": filter
                })
                logger.info(f"Created webhook for topic {topic}")
        except ResourceNotFound as e:
            logger.error(f"Resource not found when updating webhook for topic {topic}: {e}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")