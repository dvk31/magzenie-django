from rest_framework import serializers

class PrintOptionPaperTypeSerializer(serializers.Serializer):
    type = serializers.CharField()
    price_per_unit = serializers.FloatField()

class PrintOptionFinishSerializer(serializers.Serializer):
    type = serializers.CharField()
    additional_cost = serializers.FloatField()

class PrintOptionSizeSerializer(serializers.Serializer):
    size = serializers.CharField()
    dimensions = serializers.CharField()

class PrintOptionShippingSerializer(serializers.Serializer):
    method = serializers.CharField()
    estimated_delivery = serializers.CharField()
    cost = serializers.FloatField()

class PrintOptionsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    paper_types = PrintOptionPaperTypeSerializer(many=True)
    finish_options = PrintOptionFinishSerializer(many=True)
    sizes = PrintOptionSizeSerializer(many=True)
    shipping_options = PrintOptionShippingSerializer(many=True)

class CalculatePrintCostRequestSerializer(serializers.Serializer):
    magazine_id = serializers.CharField()
    quantity = serializers.IntegerField()
    paper_type = serializers.CharField()
    finish = serializers.CharField()
    size = serializers.CharField()
    shipping_method = serializers.CharField()
    shipping_address = serializers.JSONField()
    promo_code = serializers.CharField(required=False)

class PrintCostBreakdownSerializer(serializers.Serializer):
    base_cost = serializers.FloatField()
    finish_cost = serializers.FloatField()
    shipping_cost = serializers.FloatField()
    taxes = serializers.FloatField()
    discount = serializers.FloatField()
    total_cost = serializers.FloatField()

class CalculatePrintCostResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    cost_breakdown = PrintCostBreakdownSerializer()
    message = serializers.CharField()

class PlacePrintOrderRequestSerializer(serializers.Serializer):
    magazine_id = serializers.CharField()
    quantity = serializers.IntegerField()
    paper_type = serializers.CharField()
    finish = serializers.CharField()
    size = serializers.CharField()
    shipping_method = serializers.CharField()
    shipping_address_id = serializers.CharField()
    payment_method_id = serializers.CharField()
    billing_address_id = serializers.CharField()
    promo_code = serializers.CharField(required=False)
    agree_terms = serializers.BooleanField()

class PlacePrintOrderResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    order_id = serializers.CharField()
    message = serializers.CharField()
    estimated_delivery_date = serializers.DateField()

class PrintOrderStatusResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    order_id = serializers.CharField()
    status = serializers.ChoiceField(choices=["Processing", "Printed", "Shipped", "Delivered"])
    tracking_number = serializers.CharField()
    carrier = serializers.CharField()
    estimated_delivery_date = serializers.DateField()

class PrintOrderHistoryItemSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    magazine_title = serializers.CharField()
    quantity = serializers.IntegerField()
    order_date = serializers.DateField()
    status = serializers.CharField()
    total_cost = serializers.FloatField()

class PrintOrderHistoryResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    orders = PrintOrderHistoryItemSerializer(many=True)