import logging
import hmac
import hashlib
import base64
import json
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.utils import extend_schema, OpenApiResponse
from user.services.shopify_connection import ShopifyConnectionManager
from user.services.get_content_url import get_shopify_video_url, get_shopify_thumbnail_url

logger = logging.getLogger(__name__)

class ProductUpdateWebhookSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    images = serializers.ListField(child=serializers.DictField(), required=False)
    media = serializers.ListField(child=serializers.DictField(), required=False)
    updated_at = serializers.DateTimeField()

class ProductUpdateWebhookResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    product_id = serializers.IntegerField()
    video_url = serializers.URLField(allow_null=True)

class ProductUpdateWebhookView(APIView):
    def verify_webhook(self, request):
        hmac_header = request.META.get('HTTP_X_SHOPIFY_HMAC_SHA256')
        webhook_secret = settings.SHOPIFY_WEBHOOK_SECRET
        digest = hmac.new(webhook_secret.encode('utf-8'), request.body, hashlib.sha256).digest()
        computed_hmac = base64.b64encode(digest).decode()
        return hmac.compare_digest(computed_hmac, hmac_header)

    def parse_webhook_data(self, body):
        try:
            data = json.loads(body)
            serializer = ProductUpdateWebhookSerializer(data=data)
            if not serializer.is_valid():
                logger.error(f"Invalid webhook data: {serializer.errors}")
                return None
            return serializer.validated_data
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return None

    def update_video_url_metafield(self, shopify_manager, product_id, video_url):
        query = '''
        mutation updateProductMetafield($input: ProductInput!) {
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
        '''
        variables = {
            "input": {
                "id": f"gid://shopify/Product/{product_id}",
                "metafields": [
                    {
                        "namespace": "custom",
                        "key": "video_url",
                        "value": video_url,
                        "type": "url"
                    }
                ]
            }
        }
        return shopify_manager.execute_graphql_query(query, variables)

    @extend_schema(
        request=ProductUpdateWebhookSerializer,
        responses={
            200: OpenApiResponse(response=ProductUpdateWebhookResponseSerializer),
            400: OpenApiResponse(description="Bad Request"),
            403: OpenApiResponse(description="Forbidden"),
            500: OpenApiResponse(description="Internal Server Error"),
        }
    )
    def post(self, request):
        logger.info("Received Shopify product update webhook")

        if not self.verify_webhook(request):
            logger.warning("Invalid webhook signature")
            return Response({"detail": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

        validated_data = self.parse_webhook_data(request.body)
        if not validated_data:
            return Response({"detail": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)

        product_id = validated_data['id']
        logger.info(f"Processing update for product ID: {product_id}")

        try:
            # Use the imported function to get the video URL
            video_url = get_shopify_video_url(f"gid://shopify/Product/{product_id}")
            
            if not video_url:
                logger.info(f"No video URL found for product {product_id}")
                return Response({
                    "message": "No video URL found, no update required",
                    "product_id": product_id,
                    "video_url": None
                }, status=status.HTTP_200_OK)

            logger.info(f"Video URL found for product {product_id}: {video_url}")

            # Update the video_url metafield
            with ShopifyConnectionManager() as shopify_manager:
                update_result = self.update_video_url_metafield(shopify_manager, product_id, video_url)
                
                if update_result and 'data' in update_result and 'productUpdate' in update_result['data']:
                    if update_result['data']['productUpdate']['userErrors']:
                        errors = update_result['data']['productUpdate']['userErrors']
                        logger.error(f"Error updating product metafield: {errors}")
                        return Response({"detail": f"Error updating product metafield: {errors}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    else:
                        logger.info(f"Successfully updated video_url metafield for product {product_id}")
                        return Response({
                            "message": "Product video_url metafield updated successfully",
                            "product_id": product_id,
                            "video_url": video_url
                        }, status=status.HTTP_200_OK)
                else:
                    logger.error(f"Unexpected response from Shopify: {update_result}")
                    return Response({"detail": "Unexpected response from Shopify"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.exception(f"Error processing product update for product {product_id}")
            return Response({"detail": f"Internal Server Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)