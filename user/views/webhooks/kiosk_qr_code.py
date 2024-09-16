
#/user/views/webhooks/kiosk_qr_code.py
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
from django.db import transaction
from user.models import KioskQRCode, Kiosk, Product
from user.services.shopify_connection import ShopifyConnectionManager

logger = logging.getLogger(__name__)

class KioskQRCodeWebhookSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField()
    fields = serializers.ListField(child=serializers.DictField())

class KioskQRCodeWebhookResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    shopify_id = serializers.CharField()
    action = serializers.CharField()

class KioskQRCodeWebhookView(APIView):
    def verify_webhook(self, request):
        hmac_header = request.META.get('HTTP_X_SHOPIFY_HMAC_SHA256')
        webhook_secret = settings.SHOPIFY_WEBHOOK_SECRET
        digest = hmac.new(webhook_secret.encode('utf-8'), request.body, hashlib.sha256).digest()
        computed_hmac = base64.b64encode(digest).decode()
        return hmac.compare_digest(computed_hmac, hmac_header)

    def parse_webhook_data(self, body):
        try:
            data = json.loads(body)
            serializer = KioskQRCodeWebhookSerializer(data=data)
            if not serializer.is_valid():
                logger.error(f"Invalid webhook data: {serializer.errors}")
                return None
            return serializer.validated_data
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return None

    @extend_schema(
        request=KioskQRCodeWebhookSerializer,
        responses={
            200: OpenApiResponse(response=KioskQRCodeWebhookResponseSerializer),
            400: OpenApiResponse(description="Bad Request"),
            403: OpenApiResponse(description="Forbidden"),
            500: OpenApiResponse(description="Internal Server Error"),
        }
    )
    def post(self, request):
        logger.info("Received Shopify Kiosk QR Code metaobject webhook")

        if not self.verify_webhook(request):
            logger.warning("Invalid webhook signature")
            return Response({"detail": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

        validated_data = self.parse_webhook_data(request.body)
        if not validated_data:
            return Response({"detail": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)

        shopify_id = validated_data['id']
        metaobject_type = validated_data['type']
        fields = {field['key']: field['value'] for field in validated_data['fields']}

        if metaobject_type != 'kiosk_qr_code':
            logger.info(f"Ignoring non-kiosk_qr_code metaobject: {metaobject_type}")
            return Response({"message": "Ignored non-kiosk_qr_code metaobject"}, status=status.HTTP_200_OK)

        logger.info(f"Processing update for Kiosk QR Code metaobject ID: {shopify_id}")

        try:
            with transaction.atomic():
                action = self.process_kiosk_qr_code(shopify_id, fields)

            return Response({
                "message": f"Kiosk QR Code metaobject {action} successfully",
                "shopify_id": shopify_id,
                "action": action
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error processing Kiosk QR Code metaobject update for {shopify_id}")
            return Response({"detail": f"Internal Server Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def process_kiosk_qr_code(self, shopify_id, fields):
        product_id = fields.get('Product')
        qr_code_url = fields.get('QR Code URL')
        qr_code_image = fields.get('QR Code Image')
        kiosk_id = fields.get('kiosk')

        try:
            product = Product.objects.get(shopify_id=product_id)
        except Product.DoesNotExist:
            logger.error(f"Product with Shopify ID {product_id} not found")
            raise

        try:
            kiosk = Kiosk.objects.get(shopify_id=kiosk_id)
        except Kiosk.DoesNotExist:
            logger.error(f"Kiosk with Shopify ID {kiosk_id} not found")
            raise

        kiosk_qr_code, created = KioskQRCode.objects.update_or_create(
            shopify_id=shopify_id,
            defaults={
                'kiosk': kiosk,
                'product': product,
                'qr_code_url': qr_code_url,
                'image_url': qr_code_image,
            }
        )

        if created:
            logger.info(f"Created new KioskQRCode: {kiosk_qr_code}")
            return "created"
        else:
            logger.info(f"Updated existing KioskQRCode: {kiosk_qr_code}")
            return "updated"

    def delete(self, request):
        logger.info("Received Shopify Kiosk QR Code metaobject delete webhook")

        if not self.verify_webhook(request):
            logger.warning("Invalid webhook signature")
            return Response({"detail": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

        validated_data = self.parse_webhook_data(request.body)
        if not validated_data:
            return Response({"detail": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)

        shopify_id = validated_data['id']

        try:
            with transaction.atomic():
                kiosk_qr_code = KioskQRCode.objects.get(shopify_id=shopify_id)
                kiosk_qr_code.delete()
                logger.info(f"Deleted KioskQRCode with Shopify ID: {shopify_id}")

            return Response({
                "message": "Kiosk QR Code metaobject deleted successfully",
                "shopify_id": shopify_id,
                "action": "deleted"
            }, status=status.HTTP_200_OK)

        except KioskQRCode.DoesNotExist:
            logger.warning(f"Attempted to delete non-existent KioskQRCode with Shopify ID: {shopify_id}")
            return Response({
                "message": "Kiosk QR Code metaobject not found",
                "shopify_id": shopify_id,
                "action": "not_found"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error deleting Kiosk QR Code metaobject for {shopify_id}")
            return Response({"detail": f"Internal Server Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)