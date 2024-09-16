from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.core.exceptions import ObjectDoesNotExist
from user.models import ScanEvent, Kiosk, Product, KioskQRCode
from user.services.shopify_connection import ShopifyConnectionManager
from django.conf import settings
import logging
import traceback
import uuid
import shopify
from shopify import Session, ShopifyResource, Shop, Product as ShopifyProduct
from shopify.utils import shop_url
import re
import json
from django.core.serializers.json import DjangoJSONEncoder
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
            shopify_data = self.create_shopify_session(scan_event)
            
            if shopify_data:
                scan_event.shopify_id = str(uuid.uuid4())  # Generate a unique identifier
                scan_event.save()
                logger.info(f"Scan event created successfully. ID: {scan_event.id}, Shopify Session ID: {scan_event.shopify_id}")
                
                response_data = ScanEventResponseSerializer(scan_event).data
                response_data['shopify_data'] = shopify_data
                
                # Use DjangoJSONEncoder to handle any remaining non-serializable objects
                return Response(json.loads(json.dumps(response_data, cls=DjangoJSONEncoder)), status=status.HTTP_201_CREATED)
            else:
                scan_event.delete()
                return Response({"error": "Failed to create Shopify session"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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



    def create_shopify_session(self, scan_event):
        try:
            with ShopifyConnectionManager() as shopify_manager:
                new_session = Session(
                    shop_url=settings.SHOPIFY_STORE_URL,
                    version=settings.SHOPIFY_API_VERSION,
                    token=settings.SHOPIFY_ADMIN_ACCESS_TOKEN
                )

                ShopifyResource.activate_session(new_session)

                # Fetch shop information
                shop = Shop.current()
                
                # Extract numeric ID from GraphQL Global ID
                match = re.search(r'Product/(\d+)', scan_event.product.shopify_id)
                if match:
                    numeric_product_id = match.group(1)
                else:
                    raise ValueError(f"Invalid product ID format: {scan_event.product.shopify_id}")

                # Fetch product information using the numeric ID
                shopify_product = ShopifyProduct.find(numeric_product_id)

                ShopifyResource.clear_session()

                return {
                    'shop_info': {
                        'name': shop.name,
                        'email': shop.email,
                        'domain': shop.domain,
                        'country': shop.country_name,
                        'currency': shop.currency,
                    },
                    'product_info': {
                        'id': shopify_product.id,
                        'title': shopify_product.title,
                        'vendor': shopify_product.vendor,
                        'product_type': shopify_product.product_type,
                        'tags': shopify_product.tags,
                        'variants': [
                            {
                                'id': variant.id,
                                'title': variant.title,
                                'price': str(variant.price),  # Convert Decimal to string
                                'sku': variant.sku,
                            } for variant in shopify_product.variants
                        ],
                    },
                    # Add any other information you want to include
                }

        except Exception as e:
            logger.error(f"Failed to create Shopify session or fetch data: {str(e)}")
            return None