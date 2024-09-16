import logging
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
from user.models import Kiosk, Product, KioskQRCode
from rest_framework import serializers

logger = logging.getLogger(__name__)

class ProductSerializer(serializers.ModelSerializer):
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'title', 'description', 'price', 'thumbnail_url', 'video_url', 'qr_code_url']

    def get_qr_code_url(self, obj):
        kiosk = self.context.get('kiosk')
        qr_code = KioskQRCode.objects.filter(kiosk=kiosk, product=obj).first()
        return qr_code.image_url if qr_code else None

class KioskProductResponseSerializer(serializers.Serializer):
    kiosk_id = serializers.CharField()
    kiosk_name = serializers.CharField()
    store_name = serializers.CharField(allow_null=True)
    scanned_product = ProductSerializer()
    other_products = ProductSerializer(many=True)



class KioskProductsView(APIView):

    @extend_schema(
        responses={
            200: OpenApiResponse(response=KioskProductResponseSerializer),
            404: OpenApiResponse(description="Not Found"),
            500: OpenApiResponse(description="Internal Server Error"),
        }
    )
    def get(self, request, kiosk_id, scanned_product_id):
        logger.debug(f"Received request for kiosk_id: {kiosk_id}, product_id: {scanned_product_id}")
        try:
            kiosk = get_object_or_404(Kiosk, id=kiosk_id)
            scanned_product = get_object_or_404(Product, id=scanned_product_id)

            # Ensure the scanned product is associated with the kiosk
            get_object_or_404(KioskQRCode, kiosk=kiosk, product=scanned_product)

            # Get all products for this kiosk
            kiosk_products = Product.objects.filter(qr_codes__kiosk=kiosk).exclude(id=scanned_product_id)

            scanned_product_data = ProductSerializer(scanned_product, context={'kiosk': kiosk}).data
            other_products_data = ProductSerializer(kiosk_products, many=True, context={'kiosk': kiosk}).data

            response_data = {
                "kiosk_id": str(kiosk.id),
                "kiosk_name": kiosk.name,
                "store_name": kiosk.store.name if kiosk.store else None,
                "scanned_product": scanned_product_data,
                "other_products": other_products_data
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching products for kiosk {kiosk_id} and product {scanned_product_id}: {e}")
            return Response({"detail": "Internal Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)