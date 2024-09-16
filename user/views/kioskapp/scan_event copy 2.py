from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.core.exceptions import ObjectDoesNotExist
from user.models import ScanEvent, Kiosk, Product, KioskQRCode
from user.services.shopify_connection import ShopifyConnectionManager
import logging
import traceback
import uuid
import json

logger = logging.getLogger(__name__)

class ScanEventRequestSerializer(serializers.Serializer):
    kiosk_id = serializers.CharField()
    product_id = serializers.CharField()
    device_type = serializers.CharField()
    user_agent = serializers.CharField()

class ScanEventResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanEvent
        fields = ['id', 'shopify_id', 'session_id', 'kiosk', 'product', 'kiosk_qr_code', 'timestamp', 'device_type', 'user_agent', 'ip_address']

class ScanEventView(APIView):
    @extend_schema(
        request=ScanEventRequestSerializer,
        responses={
            201: OpenApiResponse(response=ScanEventResponseSerializer),
            400: OpenApiResponse(description="Bad Request"),
            500: OpenApiResponse(description="Internal Server Error"),
        }
    )
    def post(self, request):
        logger.info("Received scan event request")
        
        serializer = ScanEventRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Invalid request data: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            scan_event = self.create_scan_event(serializer.validated_data, request.META.get('REMOTE_ADDR'))
            shopify_metaobject = self.create_shopify_metaobject(scan_event)
            
            if shopify_metaobject:
                scan_event.shopify_id = shopify_metaobject['id']
                scan_event.save()
                logger.info(f"Scan event created successfully. ID: {scan_event.id}, Shopify ID: {scan_event.shopify_id}")
                return Response(ScanEventResponseSerializer(scan_event).data, status=status.HTTP_201_CREATED)
            else:
                scan_event.delete()
                return Response({"error": "Failed to create Shopify metaobject"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Unexpected error in ScanEventView: {str(e)}")
            logger.error(traceback.format_exc())
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_scan_event(self, validated_data, ip_address):
        try:
            kiosk = Kiosk.objects.get(shopify_id=validated_data['kiosk_id'])
            product = Product.objects.get(shopify_id=validated_data['product_id'])
            kiosk_qr_code = KioskQRCode.objects.filter(kiosk=kiosk, product=product).first()

            return ScanEvent.objects.create(
                session_id=str(uuid.uuid4()),
                kiosk=kiosk,
                product=product,
                kiosk_qr_code=kiosk_qr_code,
                device_type=validated_data['device_type'],
                user_agent=validated_data['user_agent'],
                ip_address=ip_address
            )
        except ObjectDoesNotExist as e:
            logger.error(f"Object not found: {str(e)}")
            raise

    def create_shopify_metaobject(self, scan_event):
        mutation = """
        mutation createMetaobject($input: MetaobjectCreateInput!) {
        metaobjectCreate(metaobject: $input) {
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
            "input": {
                "type": "scan_event",
                "fields": [
                    {"key": "timestamp", "value": scan_event.timestamp.isoformat()},
                    {"key": "kiosk", "value": scan_event.kiosk.shopify_id},
                    {"key": "store", "value": scan_event.kiosk.store.shopify_id},
                    {"key": "product", "value": scan_event.product.shopify_id},
                    {"key": "session_id", "value": scan_event.session_id},
                    {"key": "device_type", "value": scan_event.device_type},
                    {"key": "user_agent", "value": scan_event.user_agent},
                    {"key": "ip_address", "value": scan_event.ip_address},
                ]
            }
        }

        with ShopifyConnectionManager() as shopify_manager:
            result = shopify_manager.execute_graphql_query(mutation, variables)

        if result and 'data' in result and 'metaobjectCreate' in result['data']:
            metaobject_create = result['data']['metaobjectCreate']
            if metaobject_create['userErrors']:
                errors = metaobject_create['userErrors']
                logger.error(f"Failed to create Shopify metaobject. Errors: {errors}")
                return None
            else:
                return metaobject_create['metaobject']
        else:
            logger.error(f"Unexpected response from Shopify: {result}")
            return None