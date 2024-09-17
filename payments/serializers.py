from rest_framework import serializers

class ProcessPaymentRequestSerializer(serializers.Serializer):
    amount = serializers.FloatField()
    currency = serializers.CharField()
    payment_method = serializers.JSONField()
    billing_address = serializers.JSONField()
    purpose = serializers.ChoiceField(choices=["Subscription", "PrintOrder"])
    order_id = serializers.CharField(required=False)

class ProcessPaymentResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    transaction_id = serializers.CharField()
    message = serializers.CharField()

class ApplyPromoCodeRequestSerializer(serializers.Serializer):
    promo_code = serializers.CharField()
    amount = serializers.FloatField()
    currency = serializers.CharField()

class ApplyPromoCodeResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    discount_amount = serializers.FloatField()
    new_total = serializers.FloatField()
    message = serializers.CharField()