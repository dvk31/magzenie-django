from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    ProcessPaymentRequestSerializer,
    ProcessPaymentResponseSerializer,
    ApplyPromoCodeRequestSerializer,
    ApplyPromoCodeResponseSerializer
)
from .models import Payment, PromoCode
from django.conf import settings

class PaymentViewSet(viewsets.ViewSet):
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'], url_path='payments')
    def process_payment(self, request):
        serializer = ProcessPaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Implement payment processing logic, e.g., integrating with Stripe or another gateway
        transaction_id = "txn_12345"  # Placeholder
        Payment.objects.create(
            user=request.user,
            amount=data['amount'],
            currency=data['currency'],
            payment_method=data['payment_method'],
            billing_address=data['billing_address'],
            purpose=data['purpose'],
            order_id=data.get('order_id'),
            transaction_id=transaction_id
        )
        response_serializer = ProcessPaymentResponseSerializer({
            "success": True,
            "transaction_id": transaction_id,
            "message": "Payment processed successfully."
        })
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='promo-codes/apply')
    def apply_promo_code(self, request):
        serializer = ApplyPromoCodeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            promo = PromoCode.objects.get(code=data['promo_code'], is_active=True)
            discount = data['amount'] * (promo.discount_percentage / 100)
            new_total = data['amount'] - discount
            return Response({
                "success": True,
                "discount_amount": discount,
                "new_total": new_total,
                "message": "Promo code applied successfully."
            }, status=status.HTTP_200_OK)
        except PromoCode.DoesNotExist:
            return Response({"success": False, "message": "Invalid or expired promo code."},
                            status=status.HTTP_404_NOT_FOUND)