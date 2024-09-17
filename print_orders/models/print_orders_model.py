# print_orders/models.py
from django.db import models
from django.conf import settings
from core.models import BaseModel
from magazines.models import Magazine
from payments.models import PaymentMethod, Address, PromoCode
import datetime

class PrintOption(BaseModel):
    OPTION_TYPES = [
        ('paper_type', 'Paper Type'),
        ('finish', 'Finish'),
        ('size', 'Size'),
        ('shipping', 'Shipping'),
    ]

    option_type = models.CharField(max_length=50, choices=OPTION_TYPES)
    name = models.CharField(max_length=100)
    price_per_unit = models.FloatField(null=True, blank=True)
    additional_cost = models.FloatField(null=True, blank=True)
    dimensions = models.CharField(max_length=50, null=True, blank=True)
    estimated_delivery = models.CharField(max_length=100, null=True, blank=True)
    cost = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"PrintOption {self.id}: {self.get_option_type_display()} - {self.name}"

class PrintOrder(BaseModel):
    STATUS_CHOICES = [
        ('Processing', 'Processing'),
        ('Printed', 'Printed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='print_orders')
    magazine = models.ForeignKey(Magazine, on_delete=models.CASCADE, related_name='print_orders')
    quantity = models.IntegerField()
    paper_type = models.ForeignKey(PrintOption, on_delete=models.SET_NULL, null=True, related_name='print_orders_paper')
    finish = models.ForeignKey(PrintOption, on_delete=models.SET_NULL, null=True, related_name='print_orders_finish')
    size = models.ForeignKey(PrintOption, on_delete=models.SET_NULL, null=True, related_name='print_orders_size')
    shipping_method = models.ForeignKey(PrintOption, on_delete=models.SET_NULL, null=True, related_name='print_orders_shipping')
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, related_name='print_orders_shipping_address')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, related_name='print_orders_payment_method')
    billing_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, related_name='print_orders_billing_address')
    promo_code = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, null=True, blank=True, related_name='print_orders_promo_codes')
    agree_terms = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Processing')
    estimated_delivery_date = models.DateField()
    tracking_number = models.CharField(max_length=100, null=True, blank=True)
    carrier = models.CharField(max_length=100, null=True, blank=True)
    total_cost = models.FloatField(default=0.0)

    def __str__(self):
        return f"PrintOrder {self.id} by {self.user.email}"

    def calculate_total_cost(self):
        base_cost = self.quantity * self.paper_type.price_per_unit
        finish_cost = self.quantity * self.finish.additional_cost
        shipping_cost = self.shipping_method.cost
        taxes = (base_cost + finish_cost + shipping_cost) * 0.1
        discount = 0.0
        if self.promo_code and self.promo_code.is_active and self.promo_code.valid_from <= datetime.datetime.now() <= self.promo_code.valid_to:
            discount = base_cost * (self.promo_code.discount_percentage / 100)
        self.total_cost = base_cost + finish_cost + shipping_cost + taxes - discount
        self.save()

    def save(self, *args, **kwargs):
        if not self.total_cost:
            self.calculate_total_cost()
        super().save(*args, **kwargs)