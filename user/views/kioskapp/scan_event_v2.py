from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.core.exceptions import ObjectDoesNotExist
from user.models import ScanEvent, Kiosk, Product, KioskQRCode, CustomerJourney
from user.services.shopify_connection import ShopifyConnectionManager
from django.conf import settings
import logging
import traceback
import uuid
import json
from django.core.serializers.json import DjangoJSONEncoder
from .get_geolocation import get_geolocation  
from django.core.files.storage import default_storage
from rest_framework.renderers import JSONRenderer


logger = logging.getLogger(__name__)

class ScanEventRequestSerializer(serializers.Serializer):
    kiosk_id = serializers.CharField()
    product_id = serializers.CharField()
    device_type = serializers.CharField()
    user_agent = serializers.CharField()
    shopify_cart_id = serializers.CharField()

class ScanEventResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanEvent
        fields = ['id', 'shopify_id', 'session_id', 'kiosk', 'product', 'kiosk_qr_code', 'timestamp', 'device_type', 'user_agent', 'ip_address']

class ScanEventView2(APIView):
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
            
            # Use the Shopify cart ID as the session ID
            scan_event.session_id = serializer.validated_data['shopify_cart_id']
            scan_event.save()

            shopify_data = self.fetch_shopify_data(scan_event)
            
            if not shopify_data:
                logger.error("Failed to fetch Shopify data")
                return Response({"error": "Failed to fetch Shopify data"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            shopify_metaobject = self.create_shopify_metaobject(scan_event)
            
            if shopify_metaobject:
                scan_event.shopify_id = shopify_metaobject['id']
                scan_event.save()
                
                customer_journey = self.create_or_update_customer_journey(scan_event)
                
                response_data = self.prepare_response_data(scan_event, shopify_data, customer_journey)
                
                logger.info(f"Scan event created successfully. ID: {scan_event.id}, Shopify ID: {scan_event.shopify_id}")
                
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                scan_event.delete()
                return Response({"error": "Failed to create Shopify metaobject"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Unexpected error in ScanEventView: {str(e)}")
            logger.error(traceback.format_exc())
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    def create_scan_event(self, validated_data, ip_address):
        try:
            # Fetch the kiosk
            try:
                kiosk = Kiosk.objects.get(shopify_id=validated_data['kiosk_id'])
            except Kiosk.DoesNotExist:
                logger.error(f"Kiosk with shopify_id {validated_data['kiosk_id']} not found")
                raise ValueError(f"Invalid kiosk_id: {validated_data['kiosk_id']}")

            # Fetch the product
            try:
                product = Product.objects.get(shopify_id=validated_data['product_id'])
            except Product.DoesNotExist:
                logger.error(f"Product with shopify_id {validated_data['product_id']} not found")
                raise ValueError(f"Invalid product_id: {validated_data['product_id']}")

            # Try to get the KioskQRCode if it exists
            kiosk_qr_code = KioskQRCode.objects.filter(kiosk=kiosk, product=product).first()

            # Create the ScanEvent
            scan_event = ScanEvent.objects.create(
                session_id=validated_data['shopify_cart_id'],
                kiosk=kiosk,
                product=product,
                kiosk_qr_code=kiosk_qr_code,
                device_type=validated_data['device_type'],
                user_agent=validated_data['user_agent'],
                ip_address=ip_address
            )

            logger.info(f"Created ScanEvent: id={scan_event.id}, session_id={scan_event.session_id}")

            return scan_event

        except ValueError as ve:
            # Re-raise ValueError to be caught in the calling method
            raise

        except Exception as e:
            logger.error(f"Unexpected error in create_scan_event: {str(e)}")
            raise



    def fetch_shopify_data(self, scan_event):
        try:
            with ShopifyConnectionManager() as shopify_manager:
                shop = shopify_manager.get_shop_info()
                product = shopify_manager.get_product_info(scan_event.product.shopify_id)

                if not shop or not product:
                    logger.error("Failed to fetch shop or product data from Shopify")
                    return None

                return {
                    'shop_info': shop,  # shop is already a dictionary, so we can use it directly
                    'product_info': {
                        'id': product.get('id'),
                        'title': product.get('title'),
                        'vendor': product.get('vendor'),
                        'product_type': product.get('product_type'),
                        'tags': product.get('tags'),
                        'variants': [
                            {
                                'id': variant.get('id', ''),
                                'title': variant.get('title', ''),
                                'price': str(variant.get('price', '')),
                                'sku': variant.get('sku', ''),
                            } for variant in product.get('variants', [])
                        ],
                    },
                }
        except Exception as e:
            logger.error(f"Failed to fetch Shopify data: {str(e)}")
            logger.error(traceback.format_exc())  # Add this line to get the full traceback
            return None

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

    def create_or_update_customer_journey(self, scan_event):
        # This is a simplified version. You might want to expand this based on your specific requirements
        customer_journey, created = CustomerJourney.objects.get_or_create(
            session_id=scan_event.session_id,
            defaults={
                'customer': None,  # You might want to associate with a customer if they're logged in
                'initial_scan_event': scan_event,
                'conversion_status': 'initial_scan',
            }
        )
        if not created:
            customer_journey.last_interaction = scan_event.timestamp
            customer_journey.save()
        return customer_journey


    def prepare_response_data(self, scan_event, shopify_data, customer_journey):
        geolocation = get_geolocation(scan_event.ip_address)
        
        def get_file_url(file_field):
            if file_field and hasattr(file_field, 'url'):
                return file_field.url
            return None

        return {
            "scan_event": {
                "id": str(scan_event.id),  # Convert UUID to string
                "shopify_id": scan_event.shopify_id,
                "session_id": scan_event.session_id,
                "timestamp": scan_event.timestamp.isoformat(),  # Convert datetime to ISO format string
                "device_type": scan_event.device_type,
                "user_agent": scan_event.user_agent,
                "ip_address": scan_event.ip_address,
                "geolocation": geolocation,
            },
            "kiosk": {
                "id": scan_event.kiosk.shopify_id,
                "name": scan_event.kiosk.name,
                "store": {
                    "id": scan_event.kiosk.store.shopify_id,
                    "name": scan_event.kiosk.store.name,
                    "url": getattr(scan_event.kiosk.store, 'store_url', None),
                },
            },
            "product": {
                "id": scan_event.product.shopify_id,
                "title": shopify_data['product_info']['title'],
                "vendor": shopify_data['product_info']['vendor'],
                "product_type": shopify_data['product_info']['product_type'],
                "tags": shopify_data['product_info']['tags'],
                "variants": shopify_data['product_info']['variants'],
                "kiosk_video": get_file_url(getattr(scan_event.product, 'kiosk_video', None)),
                "video_url": getattr(scan_event.product, 'video_url', None),
                "thumbnail_url": get_file_url(getattr(scan_event.product, 'thumbnail_url', None)),
            },
            "shop_info": shopify_data['shop_info'],
            "customer_journey": {
                "id": str(customer_journey.id),  # Convert UUID to string
                "customer_id": str(customer_journey.customer.id) if customer_journey.customer else None,
                "initial_scan_event": str(customer_journey.initial_scan_event.id),
                "conversion_status": customer_journey.conversion_status,
            },
        }