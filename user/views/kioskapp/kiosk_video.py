import logging
import json
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.utils import extend_schema, OpenApiResponse
from user.models import Kiosk, Product
from user.services.shopify_connection import ShopifyConnectionManager

logger = logging.getLogger(__name__)

class KioskProductSerializer(serializers.Serializer):
    id = serializers.CharField()
    shopify_id = serializers.CharField()
    title = serializers.CharField()
    price = serializers.CharField()
    video_url = serializers.CharField()
    qr_code_url = serializers.CharField()

class KioskVideoResponseSerializer(serializers.Serializer):
    kiosk_id = serializers.CharField()
    kiosk_shopify_id = serializers.CharField()
    products = KioskProductSerializer(many=True)

class KioskVideoRequestSerializer(serializers.Serializer):
    kiosk_id = serializers.CharField(required=True)
    pin_code = serializers.CharField(required=True)

class KioskVideoView(APIView):
    def get_kiosk_metaobject(self, shopify_manager, kiosk_shopify_id):
        kiosk_query = """
        query($id: ID!) {
          metaobject(id: $id) {
            id
            fields {
              key
              value
            }
          }
        }
        """
        kiosk_variables = {"id": kiosk_shopify_id}
        kiosk_result = shopify_manager.execute_graphql_query(kiosk_query, kiosk_variables)
        logger.info(f"Kiosk metaobject result: {kiosk_result}")
        return kiosk_result

    def get_qr_codes(self, shopify_manager, qr_code_ids):
        qr_codes = {}
        for qr_id in qr_code_ids:
            qr_query = """
            query($id: ID!) {
              metaobject(id: $id) {
                fields {
                  key
                  value
                }
              }
            }
            """
            qr_variables = {"id": qr_id}
            qr_result = shopify_manager.execute_graphql_query(qr_query, qr_variables)
            if qr_result and 'data' in qr_result and 'metaobject' in qr_result['data']:
                qr_fields = qr_result['data']['metaobject']['fields']
                product_id = next((field['value'] for field in qr_fields if field['key'] == 'product'), None)
                image_url = next((field['value'] for field in qr_fields if field['key'] == 'image_url'), None)
                if product_id and image_url:
                    qr_codes[product_id] = image_url
        return qr_codes

    def get_product_info(self, shopify_manager, product_id):
        product_query = """
        query($id: ID!) {
          product(id: $id) {
            id
            title
            priceRangeV2 {
              minVariantPrice {
                amount
              }
            }
            metafields(first: 10) {
              edges {
                node {
                  key
                  value
                }
              }
            }
          }
        }
        """
        product_variables = {"id": product_id}
        return shopify_manager.execute_graphql_query(product_query, product_variables)

    @extend_schema(
        request=KioskVideoRequestSerializer,
        responses={
            200: OpenApiResponse(response=KioskVideoResponseSerializer),
            400: OpenApiResponse(description="Bad Request"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not Found"),
            500: OpenApiResponse(description="Internal Server Error"),
        }
    )
    def post(self, request):
        logger.debug("Received request for kiosk videos")
        
        serializer = KioskVideoRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        kiosk_id = serializer.validated_data['kiosk_id']
        pin_code = serializer.validated_data['pin_code']

        try:
            kiosk = get_object_or_404(Kiosk, id=kiosk_id)
            
            if not kiosk.is_active:
                return Response({"detail": "Kiosk is not active"}, status=status.HTTP_403_FORBIDDEN)
            
            if kiosk.pin_code != pin_code:
                return Response({"detail": "Invalid PIN code"}, status=status.HTTP_403_FORBIDDEN)

            with ShopifyConnectionManager() as shopify_manager:
                kiosk_result = self.get_kiosk_metaobject(shopify_manager, kiosk.shopify_id)
                
                if kiosk_result and 'data' in kiosk_result and 'metaobject' in kiosk_result['data']:
                    kiosk_fields = kiosk_result['data']['metaobject']['fields']
                    kiosk_shopify_id = kiosk_result['data']['metaobject']['id']
                    product_ids = json.loads(next((field['value'] for field in kiosk_fields if field['key'] == 'products'), '[]'))
                    qr_code_ids = json.loads(next((field['value'] for field in kiosk_fields if field['key'] == 'qr_codes'), '[]'))
                    
                    logger.info(f"Product IDs: {product_ids}")
                    logger.info(f"QR code IDs: {qr_code_ids}")

                    qr_codes = self.get_qr_codes(shopify_manager, qr_code_ids)
                    logger.info(f"QR codes: {qr_codes}")

                    products_data = []
                    for product_id in product_ids:
                        product_result = self.get_product_info(shopify_manager, product_id)
                        
                        if product_result and 'data' in product_result and 'product' in product_result['data']:
                            product_data = product_result['data']['product']
                            video_url = next((metafield['node']['value'] for metafield in product_data['metafields']['edges'] if metafield['node']['key'] == 'video_url'), None)
                            
                            products_data.append({
                                "id": str(product_data['id']).split('/')[-1],
                                "shopify_id": product_data['id'],
                                "title": product_data['title'],
                                "price": product_data['priceRangeV2']['minVariantPrice']['amount'],
                                "video_url": video_url,
                                "qr_code_url": qr_codes.get(product_id)
                            })
                        else:
                            logger.warning(f"Failed to fetch Shopify data for product {product_id}")

                    logger.info(f"Products data: {products_data}")

                    response_data = {
                        "kiosk_id": str(kiosk.id),
                        "kiosk_shopify_id": kiosk_shopify_id,
                        "products": products_data
                    }

                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    logger.error(f"Failed to fetch kiosk metaobject: {kiosk_result}")
                    return Response({"detail": "Failed to fetch kiosk data"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Kiosk.DoesNotExist:
            return Response({"detail": "Kiosk not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching products for kiosk {kiosk_id}: {e}")
            return Response({"detail": "Internal Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)