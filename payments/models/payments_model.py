#payments/models/payments_model.py

from django.db import models
from django.conf import settings
from core.models import BaseModel

class Payment(BaseModel):
    PURPOSE_CHOICES = [
        ('Subscription', 'Subscription'),
        ('PrintOrder', 'Print Order'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    amount = models.FloatField()
    currency = models.CharField(max_length=10)
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.SET_NULL, null=True, related_name='payments')
    billing_address = models.ForeignKey('Address', on_delete=models.SET_NULL, null=True, related_name='billing_payments')
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    order = models.ForeignKey('print_orders.PrintOrder', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, default='Completed')

    def __str__(self):
        return f"Payment {self.id}: {self.transaction_id} by {self.user.email}"

class PromoCode(BaseModel):
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.FloatField()
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.discount_percentage}% off"

class SubscriptionPlan(BaseModel):
    PLAN_CHOICES = [
        ('Free', 'Free'),
        ('Standard', 'Standard'),
        ('Premium', 'Premium'),
    ]

    name = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True)
    price = models.FloatField()
    duration_months = models.IntegerField()
    description = models.TextField()

    def __str__(self):
        return f"SubscriptionPlan {self.id}: {self.name}"

class Subscription(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"Subscription {self.id}: {self.plan.name} for {self.user.email}"

class Address(BaseModel):
    ADDRESS_TYPES = [
        ('Billing', 'Billing'),
        ('Shipping', 'Shipping'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPES, default='Other')
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    def __str__(self):
        return f"Address {self.id}: {self.line1}, {self.city}, {self.country}"



class PaymentMethod(models.Model):
    METHOD_TYPE_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        # Add other payment types as needed
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(max_length=50, choices=METHOD_TYPE_CHOICES)
    last_four_digits = models.CharField(max_length=4)
    expiry_date = models.DateField()

    def __str__(self):
        return f"{self.get_method_type_display()} ending with {self.last_four_digits}"
