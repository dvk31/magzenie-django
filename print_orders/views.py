from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    PrintOptionsResponseSerializer,
    CalculatePrintCostRequestSerializer,
    CalculatePrintCostResponseSerializer,
    PlacePrintOrderRequestSerializer,
    PlacePrintOrderResponseSerializer,
    PrintOrderStatusResponseSerializer,
    PrintOrderHistoryResponseSerializer
)
from .models import PrintOrder, PrintOption
from magazines.models import Magazine
from payments.models import PaymentMethod, Address
from django.utils import timezone
import datetime

class PrintOrderViewSet(viewsets.ViewSet):
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='print-options')
    def get_print_options(self, request):
        paper_types = PrintOption.objects.filter(option_type='paper_type')
        finish_options = PrintOption.objects.filter(option_type='finish')
        sizes = PrintOption.objects.filter(option_type='size')
        shipping_options = PrintOption.objects.filter(option_type='shipping')
        serializer = PrintOptionsResponseSerializer({
            "success": True,
            "paper_types": paper_types.values('type', 'price_per_unit'),
            "finish_options": finish_options.values('type', 'additional_cost'),
            "sizes": sizes.values('size', 'dimensions'),
            "shipping_options": shipping_options.values('method', 'estimated_delivery', 'cost')
        })
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='print-orders/calculate')
    def calculate_print_cost(self, request):
        serializer = CalculatePrintCostRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Implement cost calculation logic based on options
        base_cost = data['quantity'] * 3.00  # Placeholder
        finish_cost = data['quantity'] * 0.75  # Placeholder
        shipping_cost = 15.00  # Placeholder
        taxes = (base_cost + finish_cost + shipping_cost) * 0.1  # 10% tax
        discount = 0.0
        if data.get('promo_code'):
            try:
                promo = PromoCode.objects.get(code=data['promo_code'], is_active=True)
                discount = base_cost * (promo.discount_percentage / 100)
            except PromoCode.DoesNotExist:
                return Response({"success": False, "message": "Invalid promo code."}, status=status.HTTP_404_NOT_FOUND)
        total_cost = base_cost + finish_cost + shipping_cost + taxes - discount
        cost_breakdown = {
            "base_cost": base_cost,
            "finish_cost": finish_cost,
            "shipping_cost": shipping_cost,
            "taxes": taxes,
            "discount": discount,
            "total_cost": total_cost
        }
        response_serializer = CalculatePrintCostResponseSerializer({
            "success": True,
            "cost_breakdown": cost_breakdown,
            "message": "Cost calculated successfully."
        })
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='print-orders')
    def place_print_order(self, request):
        serializer = PlacePrintOrderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            magazine = Magazine.objects.get(magazine_id=data['magazine_id'], user=request.user)
            shipping_address = Address.objects.get(address_id=data['shipping_address_id'], user=request.user)
            payment_method = PaymentMethod.objects.get(payment_method_id=data['payment_method_id'], user=request.user)
            billing_address = Address.objects.get(address_id=data['billing_address_id'], user=request.user)
            # Implement order placement logic
            order = PrintOrder.objects.create(
                user=request.user,
                magazine=magazine,
                quantity=data['quantity'],
                paper_type=data['paper_type'],
                finish=data['finish'],
                size=data['size'],
                shipping_method=data['shipping_method'],
                shipping_address=shipping_address,
                payment_method=payment_method,
                billing_address=billing_address,
                agree_terms=data['agree_terms'],
                status="Processing",
                estimated_delivery_date=timezone.now().date() + datetime.timedelta(days=5)  # Placeholder
            )
            return Response({
                "success": True,
                "order_id": order.order_id,
                "message": "Print order placed successfully.",
                "estimated_delivery_date": order.estimated_delivery_date
            }, status=status.HTTP_201_CREATED)
        except (Magazine.DoesNotExist, PaymentMethod.DoesNotExist, Address.DoesNotExist):
            return Response({"success": False, "error": "Invalid magazine, payment method, or address."},
                            status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='print-orders/history')
    def order_history(self, request):
        orders = PrintOrder.objects.filter(user=request.user)
        serializer = PrintOrderHistoryResponseSerializer({
            "success": True,
            "orders": [
                {
                    "order_id": order.order_id,
                    "magazine_title": order.magazine.title,
                    "quantity": order.quantity,
                    "order_date": order.order_date,
                    "status": order.status,
                    "total_cost": order.total_cost
                } for order in orders
            ]
        })
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='print-orders/(?P<order_id>[^/.]+)/status')
    def order_status(self, request, order_id=None):
        try:
            order = PrintOrder.objects.get(order_id=order_id, user=request.user)
            serializer = PrintOrderStatusResponseSerializer({
                "success": True,
                "order_id": order.order_id,
                "status": order.status,
                "tracking_number": order.tracking_number,
                "carrier": order.carrier,
                "estimated_delivery_date": order.estimated_delivery_date
            })
            return Response(serializer.data, status=status.HTTP_200_OK)
        except PrintOrder.DoesNotExist:
            return Response({"success": False, "error": "Print order not found."}, status=status.HTTP_404_NOT_FOUND)