import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.contrib.postgres.fields import JSONField  # Use if Django < 3.1

# For Django 3.1 and above, you can use the built-in JSONField
# from django.db.models import JSONField

# ==========================
# Enumerations
# ==========================

class CartTypeEnum(models.TextChoices):
    TYPE1 = 'type1', 'Type 1'
    TYPE2 = 'type2', 'Type 2'
    # Add other types as needed

class ClaimItemReasonEnum(models.TextChoices):
    DAMAGE = 'damage', 'Damage'
    WRONG_ITEM = 'wrong_item', 'Wrong Item'
    # Add other reasons as needed

class DiscountConditionTypeEnum(models.TextChoices):
    TYPE_A = 'type_a', 'Type A'
    TYPE_B = 'type_b', 'Type B'
    # Add other types as needed

class DiscountConditionOperatorEnum(models.TextChoices):
    EQUAL = 'equal', 'Equal'
    NOT_EQUAL = 'not_equal', 'Not Equal'
    # Add other operators as needed

class DiscountRuleTypeEnum(models.TextChoices):
    FIXED = 'fixed', 'Fixed'
    PERCENTAGE = 'percentage', 'Percentage'
    # Add other types as needed

class DiscountRuleAllocationEnum(models.TextChoices):
    EACH = 'each', 'Each'
    TOTAL = 'total', 'Total'
    # Add other allocations as needed

class OrderStatusEnum(models.TextChoices):
    PENDING = 'pending', 'Pending'
    COMPLETED = 'completed', 'Completed'
    CANCELED = 'canceled', 'Canceled'
    # Add other statuses as needed

class UserRoleEnum(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    CUSTOMER = 'customer', 'Customer'
    SUPPLIER = 'supplier', 'Supplier'
    # Add other roles as needed

class PaymentCollectionTypeEnum(models.TextChoices):
    TYPE1 = 'type1', 'Type 1'
    TYPE2 = 'type2', 'Type 2'
    # Add other types as needed

class PaymentCollectionStatusEnum(models.TextChoices):
    OPEN = 'open', 'Open'
    CLOSED = 'closed', 'Closed'
    # Add other statuses as needed

class PriceListTypeEnum(models.TextChoices):
    STATIC = 'static', 'Static'
    DYNAMIC = 'dynamic', 'Dynamic'
    # Add other types as needed

class PriceListStatusEnum(models.TextChoices):
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'
    # Add other statuses as needed

class ProductStatusEnum(models.TextChoices):
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'
    # Add other statuses as needed

class ReturnStatusEnum(models.TextChoices):
    PENDING = 'pending', 'Pending'
    RECEIVED = 'received', 'Received'
    # Add other statuses as needed

# Define other enums similarly...

# ==========================
# Abstract Base Models
# ==========================

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    metadata = JSONField(null=True, blank=True)  # Use JSONField for jsonb

    class Meta:
        abstract = True

# ==========================
# Models
# ==========================

class Address(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey('Customer', null=True, blank=True, on_delete=models.SET_NULL)
    company = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    address_1 = models.CharField(max_length=255, null=True, blank=True)
    address_2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    country_code = models.CharField(max_length=10, null=True, blank=True)
    province = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}, {self.address_1}, {self.city}"

class AnalyticsConfig(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    opt_out = models.BooleanField(default=False)
    anonymize = models.BooleanField(default=False)

    def __str__(self):
        return f"AnalyticsConfig for {self.user.email}"

class BatchJob(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.TextField()
    created_by = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='batch_jobs_created')
    context = JSONField(null=True, blank=True)
    result = JSONField(null=True, blank=True)
    dry_run = models.BooleanField(default=False)
    pre_processed_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    processing_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"BatchJob {self.id} of type {self.type}"

class Cart(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(null=True, blank=True)
    billing_address = models.ForeignKey(Address, related_name='billing_carts', null=True, blank=True, on_delete=models.SET_NULL)
    shipping_address = models.ForeignKey(Address, related_name='shipping_carts', null=True, blank=True, on_delete=models.SET_NULL)
    region = models.ForeignKey('Region', on_delete=models.CASCADE)
    customer = models.ForeignKey('Customer', null=True, blank=True, on_delete=models.SET_NULL)
    payment = models.ForeignKey('Payment', null=True, blank=True, on_delete=models.SET_NULL)
    type = models.CharField(max_length=50, choices=CartTypeEnum.choices)
    completed_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)
    context = JSONField(null=True, blank=True)
    payment_authorized_at = models.DateTimeField(null=True, blank=True)
    sales_channel = models.ForeignKey('SalesChannel', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Cart {self.id}"

class CartDiscount(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    discount = models.ForeignKey('Discount', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('cart', 'discount')

    def __str__(self):
        return f"Cart {self.cart.id} - Discount {self.discount.id}"

class CartGiftCard(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    gift_card = models.ForeignKey('GiftCard', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('cart', 'gift_card')

    def __str__(self):
        return f"Cart {self.cart.id} - GiftCard {self.gift_card.id}"

class ClaimImage(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim_item = models.ForeignKey('ClaimItem', on_delete=models.CASCADE)
    url = models.URLField()
    
    def __str__(self):
        return f"ClaimImage {self.id} for ClaimItem {self.claim_item.id}"

class ClaimItem(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim_order = models.ForeignKey('ClaimOrder', on_delete=models.CASCADE)
    item = models.ForeignKey('LineItem', on_delete=models.CASCADE)
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE)
    reason = models.CharField(max_length=50, choices=ClaimItemReasonEnum.choices)
    note = models.TextField(null=True, blank=True)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"ClaimItem {self.id} for Order {self.claim_order.order.id}"

class ClaimItemTag(TimeStampedModel):
    item = models.ForeignKey(ClaimItem, on_delete=models.CASCADE)
    tag = models.ForeignKey('ClaimTag', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('item', 'tag')

    def __str__(self):
        return f"ClaimItem {self.item.id} - Tag {self.tag.value}"

class ClaimOrder(TimeStampedModel):
    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('refunded', 'Refunded'),
        # Add other statuses as needed
    ]

    FULFILLMENT_STATUS_CHOICES = [
        ('fulfilled', 'Fulfilled'),
        ('unfulfilled', 'Unfulfilled'),
        # Add other statuses as needed
    ]

    TYPE_CHOICES = [
        ('type1', 'Type 1'),
        ('type2', 'Type 2'),
        # Add other types as needed
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES)
    fulfillment_status = models.CharField(max_length=50, choices=FULFILLMENT_STATUS_CHOICES)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    order = models.ForeignKey('Order', on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.SET_NULL)
    refund_amount = models.PositiveIntegerField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)
    no_notification = models.BooleanField(default=False)

    def __str__(self):
        return f"ClaimOrder {self.id} for Order {self.order.id}"

class ClaimTag(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    value = models.CharField(max_length=255)

    def __str__(self):
        return self.value

class Country(TimeStampedModel):
    id = models.AutoField(primary_key=True)
    iso_2 = models.CharField(max_length=2)
    iso_3 = models.CharField(max_length=3)
    num_code = models.IntegerField()
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    region = models.ForeignKey('Region', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.name

class Currency(TimeStampedModel):
    code = models.CharField(max_length=10, primary_key=True)
    symbol = models.CharField(max_length=10)
    symbol_native = models.CharField(max_length=10)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.code

class CustomShippingOption(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    price = models.PositiveIntegerField()
    shipping_option = models.ForeignKey('ShippingOption', on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"CustomShippingOption {self.id} for ShippingOption {self.shipping_option.id}"

class Customer(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    billing_address = models.ForeignKey(Address, related_name='billing_customers', null=True, blank=True, on_delete=models.SET_NULL)
    password_hash = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    has_account = models.BooleanField(default=False)

    def __str__(self):
        return self.email

class CustomerGroup(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    # Additional fields can be added as needed

    def __str__(self):
        return self.name

class CustomerGroupCustomers(TimeStampedModel):
    customer_group = models.ForeignKey(CustomerGroup, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('customer_group', 'customer')

    def __str__(self):
        return f"Group {self.customer_group.name} - Customer {self.customer.email}"

class Discount(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    is_dynamic = models.BooleanField(default=False)
    rule = models.ForeignKey('DiscountRule', null=True, blank=True, on_delete=models.SET_NULL)
    is_disabled = models.BooleanField(default=False)
    parent_discount = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    valid_duration = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.code

class DiscountCondition(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=50, choices=DiscountConditionTypeEnum.choices)
    operator = models.CharField(max_length=50, choices=DiscountConditionOperatorEnum.choices)
    discount_rule = models.ForeignKey('DiscountRule', on_delete=models.CASCADE)

    def __str__(self):
        return f"Condition {self.id} for DiscountRule {self.discount_rule.id}"

class DiscountConditionCustomerGroup(TimeStampedModel):
    customer_group = models.ForeignKey(CustomerGroup, on_delete=models.CASCADE)
    condition = models.ForeignKey(DiscountCondition, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('customer_group', 'condition')

    def __str__(self):
        return f"Condition {self.condition.id} - CustomerGroup {self.customer_group.name}"

class DiscountConditionProduct(TimeStampedModel):
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    condition = models.ForeignKey(DiscountCondition, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product', 'condition')

    def __str__(self):
        return f"Condition {self.condition.id} - Product {self.product.title}"

class DiscountConditionProductCollection(TimeStampedModel):
    product_collection = models.ForeignKey('ProductCollection', on_delete=models.CASCADE)
    condition = models.ForeignKey(DiscountCondition, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product_collection', 'condition')

    def __str__(self):
        return f"Condition {self.condition.id} - ProductCollection {self.product_collection.title}"

class DiscountConditionProductTag(TimeStampedModel):
    product_tag = models.ForeignKey('ProductTag', on_delete=models.CASCADE)
    condition = models.ForeignKey(DiscountCondition, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product_tag', 'condition')

    def __str__(self):
        return f"Condition {self.condition.id} - ProductTag {self.product_tag.value}"

class DiscountConditionProductType(TimeStampedModel):
    product_type = models.ForeignKey('ProductType', on_delete=models.CASCADE)
    condition = models.ForeignKey(DiscountCondition, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product_type', 'condition')

    def __str__(self):
        return f"Condition {self.condition.id} - ProductType {self.product_type.value}"

class DiscountRegions(TimeStampedModel):
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE)
    region = models.ForeignKey('Region', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('discount', 'region')

    def __str__(self):
        return f"Discount {self.discount.code} - Region {self.region.name}"

class DiscountRule(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=50, choices=DiscountRuleTypeEnum.choices)
    value = models.PositiveIntegerField()
    allocation = models.CharField(max_length=50, choices=DiscountRuleAllocationEnum.choices, null=True, blank=True)

    def __str__(self):
        return f"DiscountRule {self.id} - {self.type}"

class DiscountRuleProducts(TimeStampedModel):
    discount_rule = models.ForeignKey(DiscountRule, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('discount_rule', 'product')

    def __str__(self):
        return f"DiscountRule {self.discount_rule.id} - Product {self.product.title}"

class DraftOrder(TimeStampedModel):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
        # Add other statuses as needed
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    display_id = models.PositiveIntegerField(unique=True)
    cart = models.ForeignKey(Cart, null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey('Order', null=True, blank=True, on_delete=models.SET_NULL)
    canceled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)
    no_notification_order = models.BooleanField(default=False)

    def __str__(self):
        return f"DraftOrder {self.display_id} - {self.status}"

class Fulfillment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    swap = models.ForeignKey('Swap', null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey('Order', null=True, blank=True, on_delete=models.SET_NULL)
    tracking_numbers = JSONField()
    data = JSONField()
    shipped_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    provider = models.ForeignKey('FulfillmentProvider', null=True, blank=True, on_delete=models.SET_NULL)
    claim_order = models.ForeignKey('ClaimOrder', null=True, blank=True, on_delete=models.SET_NULL)
    no_notification = models.BooleanField(default=False)
    location = models.ForeignKey('Location', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Fulfillment {self.id}"

class FulfillmentItem(TimeStampedModel):
    fulfillment = models.ForeignKey(Fulfillment, on_delete=models.CASCADE)
    item = models.ForeignKey('LineItem', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    class Meta:
        unique_together = ('fulfillment', 'item')

    def __str__(self):
        return f"FulfillmentItem {self.id} - Item {self.item.title}"

class FulfillmentProvider(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_installed = models.BooleanField(default=False)

    def __str__(self):
        return f"FulfillmentProvider {self.id}"

class GiftCard(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    value = models.PositiveIntegerField()
    balance = models.PositiveIntegerField()
    region = models.ForeignKey('Region', on_delete=models.CASCADE)
    order = models.ForeignKey('Order', null=True, blank=True, on_delete=models.SET_NULL)
    is_disabled = models.BooleanField(default=False)
    ends_at = models.DateTimeField(null=True, blank=True)
    tax_rate = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.code

class GiftCardTransaction(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gift_card = models.ForeignKey(GiftCard, on_delete=models.CASCADE)
    order = models.ForeignKey('Order', on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    is_taxable = models.BooleanField(null=True, blank=True)
    tax_rate = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Transaction {self.id} for GiftCard {self.gift_card.code}"

class IdempotencyKey(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.CharField(max_length=255, unique=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    request_method = models.CharField(max_length=10, null=True, blank=True)
    request_params = JSONField(null=True, blank=True)
    request_path = models.CharField(max_length=255, null=True, blank=True)
    response_code = models.IntegerField(null=True, blank=True)
    response_body = JSONField(null=True, blank=True)
    recovery_point = models.CharField(max_length=255)

    def __str__(self):
        return self.idempotency_key

class Image(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField()

    def __str__(self):
        return self.url

class Invite(TimeStampedModel):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
        # Add other roles as needed
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_email = models.EmailField()
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, null=True, blank=True)
    accepted = models.BooleanField(default=False)
    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"Invite {self.id} to {self.user_email}"

class LineItem(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey('Order', null=True, blank=True, on_delete=models.SET_NULL)
    swap = models.ForeignKey('Swap', null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    thumbnail = models.URLField(null=True, blank=True)
    is_giftcard = models.BooleanField(default=False)
    should_merge = models.BooleanField(default=False)
    allow_discounts = models.BooleanField(default=True)
    has_shipping = models.BooleanField(null=True, blank=True)
    unit_price = models.PositiveIntegerField()
    variant = models.ForeignKey('ProductVariant', null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.PositiveIntegerField()
    fulfilled_quantity = models.PositiveIntegerField(null=True, blank=True)
    returned_quantity = models.PositiveIntegerField(null=True, blank=True)
    shipped_quantity = models.PositiveIntegerField(null=True, blank=True)
    claim_order = models.ForeignKey('ClaimOrder', null=True, blank=True, on_delete=models.SET_NULL)
    is_return = models.BooleanField(default=False)
    original_item = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='original_items')
    order_edit = models.ForeignKey('OrderEdit', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.title

class LineItemAdjustment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(LineItem, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    discount = models.ForeignKey('Discount', null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Adjustment {self.id} for LineItem {self.item.id}"

class LineItemTaxLine(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rate = models.FloatField()
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, null=True, blank=True)
    item = models.ForeignKey(LineItem, on_delete=models.CASCADE)

    def __str__(self):
        return f"TaxLine {self.id} for LineItem {self.item.id}"

class Migration(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.BigIntegerField()
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class MoneyAmount(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    currency_code = models.CharField(max_length=10)
    amount = models.PositiveIntegerField()
    region = models.ForeignKey('Region', null=True, blank=True, on_delete=models.SET_NULL)
    min_quantity = models.PositiveIntegerField(null=True, blank=True)
    max_quantity = models.PositiveIntegerField(null=True, blank=True)
    price_list = models.ForeignKey('PriceList', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.amount} {self.currency_code}"

class Note(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    value = models.TextField()
    resource_type = models.CharField(max_length=50)
    resource_id = models.UUIDField()
    author = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Note {self.id} on {self.resource_type} {self.resource_id}"

class Notification(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_name = models.CharField(max_length=255, null=True, blank=True)
    resource_type = models.CharField(max_length=50)
    resource_id = models.UUIDField()
    customer = models.ForeignKey('Customer', null=True, blank=True, on_delete=models.SET_NULL)
    to = models.CharField(max_length=255)
    data = JSONField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='child_notifications')
    provider = models.ForeignKey('NotificationProvider', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Notification {self.id} to {self.to}"

class NotificationProvider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_installed = models.BooleanField(default=False)

    def __str__(self):
        return f"NotificationProvider {self.id}"

class OAuth(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField(max_length=255)
    application_name = models.CharField(max_length=255)
    install_url = models.URLField(null=True, blank=True)
    uninstall_url = models.URLField(null=True, blank=True)
    data = JSONField(null=True, blank=True)

    def __str__(self):
        return self.display_name

class OnboardingState(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    current_step = models.CharField(max_length=255, null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    product = models.ForeignKey('Product', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"OnboardingState {self.id} - {'Complete' if self.is_complete else 'Incomplete'}"

class Order(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=50, choices=OrderStatusEnum.choices)
    fulfillment_status = models.CharField(max_length=50, choices=[
        ('fulfilled', 'Fulfilled'),
        ('unfulfilled', 'Unfulfilled'),
        # Add other statuses as needed
    ])
    payment_status = models.CharField(max_length=50, choices=[
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('refunded', 'Refunded'),
        # Add other statuses as needed
    ])
    display_id = models.PositiveIntegerField(unique=True)
    cart = models.ForeignKey(Cart, null=True, blank=True, on_delete=models.SET_NULL)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    email = models.EmailField()
    billing_address = models.ForeignKey(Address, related_name='billing_orders', null=True, blank=True, on_delete=models.SET_NULL)
    shipping_address = models.ForeignKey(Address, related_name='shipping_orders', null=True, blank=True, on_delete=models.SET_NULL)
    region = models.ForeignKey('Region', on_delete=models.CASCADE)
    currency_code = models.CharField(max_length=10)
    tax_rate = models.FloatField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)
    draft_order = models.ForeignKey(DraftOrder, null=True, blank=True, on_delete=models.SET_NULL)
    no_notification = models.BooleanField(default=False)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    sales_channel = models.ForeignKey('SalesChannel', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Order {self.display_id} - {self.status}"

class OrderDiscount(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('order', 'discount')

    def __str__(self):
        return f"Order {self.order.display_id} - Discount {self.discount.code}"

class OrderEdit(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    internal_note = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE, related_name='order_edits_created')
    requested_by = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='order_edits_requested')
    requested_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='order_edits_confirmed')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    declined_by = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='order_edits_declined')
    declined_reason = models.TextField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    canceled_by = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='order_edits_canceled')
    canceled_at = models.DateTimeField(null=True, blank=True)
    payment_collection = models.ForeignKey('PaymentCollection', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"OrderEdit {self.id} for Order {self.order.display_id}"

class OrderGiftCard(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    gift_card = models.ForeignKey(GiftCard, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('order', 'gift_card')

    def __str__(self):
        return f"Order {self.order.display_id} - GiftCard {self.gift_card.code}"

class OrderItemChange(TimeStampedModel):
    TYPE_CHOICES = [
        ('addition', 'Addition'),
        ('removal', 'Removal'),
        # Add other types as needed
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    order_edit = models.ForeignKey(OrderEdit, on_delete=models.CASCADE)
    original_line_item = models.ForeignKey(LineItem, null=True, blank=True, on_delete=models.SET_NULL, related_name='original_changes')
    line_item = models.ForeignKey(LineItem, null=True, blank=True, on_delete=models.SET_NULL, related_name='changes')

    def __str__(self):
        return f"OrderItemChange {self.id} - {self.type}"

class Payment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    swap = models.ForeignKey('Swap', null=True, blank=True, on_delete=models.SET_NULL)
    cart = models.ForeignKey(Cart, null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    currency_code = models.CharField(max_length=10)
    amount_refunded = models.PositiveIntegerField(default=0)
    provider = models.ForeignKey('PaymentProvider', on_delete=models.CASCADE)
    data = JSONField()
    captured_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Payment {self.id} - {self.amount} {self.currency_code}"

class PaymentCollection(TimeStampedModel):
    TYPE_CHOICES = PaymentCollectionTypeEnum.choices
    STATUS_CHOICES = PaymentCollectionStatusEnum.choices

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    description = models.TextField(null=True, blank=True)
    amount = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    authorized_amount = models.PositiveIntegerField(null=True, blank=True)
    region = models.ForeignKey('Region', on_delete=models.CASCADE)
    currency_code = models.CharField(max_length=10)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE)

    def __str__(self):
        return f"PaymentCollection {self.id} - {self.status}"

class PaymentCollectionPayments(TimeStampedModel):
    payment_collection = models.ForeignKey(PaymentCollection, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('payment_collection', 'payment')

    def __str__(self):
        return f"PaymentCollection {self.payment_collection.id} - Payment {self.payment.id}"

class PaymentCollectionSessions(TimeStampedModel):
    payment_collection = models.ForeignKey(PaymentCollection, on_delete=models.CASCADE)
    payment_session = models.ForeignKey('PaymentSession', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('payment_collection', 'payment_session')

    def __str__(self):
        return f"PaymentCollection {self.payment_collection.id} - PaymentSession {self.payment_session.id}"

class PaymentProvider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_installed = models.BooleanField(default=False)

    def __str__(self):
        return f"PaymentProvider {self.id}"

class PaymentSession(TimeStampedModel):
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        # Add other statuses as needed
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, null=True, blank=True, on_delete=models.SET_NULL)
    provider = models.ForeignKey(PaymentProvider, on_delete=models.CASCADE)
    is_selected = models.BooleanField(default=False)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    data = JSONField()
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)
    payment_authorized_at = models.DateTimeField(null=True, blank=True)
    amount = models.PositiveIntegerField(null=True, blank=True)
    is_initiated = models.BooleanField(default=False)

    def __str__(self):
        return f"PaymentSession {self.id} - {self.status}"

class PriceList(TimeStampedModel):
    TYPE_CHOICES = PriceListTypeEnum.choices
    STATUS_CHOICES = PriceListStatusEnum.choices

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class PriceListCustomerGroup(TimeStampedModel):
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE)
    customer_group = models.ForeignKey(CustomerGroup, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('price_list', 'customer_group')

    def __str__(self):
        return f"PriceList {self.price_list.name} - CustomerGroup {self.customer_group.name}"

class Product(TimeStampedModel):
    STATUS_CHOICES = ProductStatusEnum.choices

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    handle = models.SlugField(max_length=255, unique=True, null=True, blank=True)
    is_giftcard = models.BooleanField(default=False)
    thumbnail = models.ImageField(upload_to='product_images/', null=True, blank=True)
    weight = models.PositiveIntegerField(null=True, blank=True)
    length = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    hs_code = models.CharField(max_length=50, null=True, blank=True)
    origin_country = models.CharField(max_length=10, null=True, blank=True)
    mid_code = models.CharField(max_length=50, null=True, blank=True)
    material = models.CharField(max_length=255, null=True, blank=True)
    collection = models.ForeignKey('ProductCollection', null=True, blank=True, on_delete=models.SET_NULL)
    type = models.ForeignKey('ProductType', null=True, blank=True, on_delete=models.SET_NULL)
    discountable = models.BooleanField(default=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    ai_generated_content = models.TextField(null=True, blank=True)
    is_ai_generated = models.BooleanField(default=False)
    amazon_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amazon_review_star = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    amazon_review_count = models.PositiveIntegerField(null=True, blank=True)
    hashtags = models.JSONField(null=True, blank=True)
    emojis = models.JSONField(null=True, blank=True)
    features = models.TextField(null=True, blank=True)
    supplier = models.ForeignKey('ProductSupplier', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.title

class ProductCategory(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    handle = models.SlugField(max_length=255, unique=True)
    parent_category = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='subcategories')
    mpath = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_internal = models.BooleanField(default=False)
    rank = models.PositiveIntegerField()
    description = models.TextField()

    def __str__(self):
        return self.name

class ProductCategoryProduct(TimeStampedModel):
    product_category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product_category', 'product')

    def __str__(self):
        return f"Category {self.product_category.name} - Product {self.product.title}"

class ProductCollection(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    handle = models.SlugField(max_length=255, unique=True, null=True, blank=True)

    def __str__(self):
        return self.title

class ProductImages(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product', 'image')

    def __str__(self):
        return f"Product {self.product.title} - Image {self.image.url}"

class ProductOption(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.title

class ProductOptionValue(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    value = models.CharField(max_length=255)
    option = models.ForeignKey(ProductOption, on_delete=models.CASCADE)
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE)

    def __str__(self):
        return self.value

class ProductSalesChannel(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    sales_channel = models.ForeignKey('SalesChannel', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product', 'sales_channel')

    def __str__(self):
        return f"Product {self.product.title} - SalesChannel {self.sales_channel.name}"

class ProductShippingProfile(TimeStampedModel):
    profile = models.ForeignKey('ShippingProfile', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('profile', 'product')

    def __str__(self):
        return f"Product {self.product.title} - ShippingProfile {self.profile.name}"

class ProductSupplier(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    address = models.TextField()
    is_approved = models.BooleanField(default=False)
    user = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.company_name

class ProductTag(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    value = models.CharField(max_length=255)

    def __str__(self):
        return self.value

class ProductTags(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_tag = models.ForeignKey(ProductTag, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product', 'product_tag')

    def __str__(self):
        return f"Product {self.product.title} - Tag {self.product_tag.value}"

class ProductTaxRate(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    tax_rate = models.ForeignKey('TaxRate', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product', 'tax_rate')

    def __str__(self):
        return f"Product {self.product.title} - TaxRate {self.tax_rate.name}"

class ProductType(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    value = models.CharField(max_length=255)

    def __str__(self):
        return self.value

class ProductTypeTaxRate(TimeStampedModel):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    tax_rate = models.ForeignKey('TaxRate', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product_type', 'tax_rate')

    def __str__(self):
        return f"ProductType {self.product_type.value} - TaxRate {self.tax_rate.name}"

class ProductVariant(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    sku = models.CharField(max_length=255, null=True, blank=True)
    barcode = models.CharField(max_length=255, null=True, blank=True)
    ean = models.CharField(max_length=255, null=True, blank=True)
    upc = models.CharField(max_length=255, null=True, blank=True)
    inventory_quantity = models.PositiveIntegerField(default=0)
    allow_backorder = models.BooleanField(default=False)
    manage_inventory = models.BooleanField(default=True)
    hs_code = models.CharField(max_length=50, null=True, blank=True)
    origin_country = models.CharField(max_length=10, null=True, blank=True)
    mid_code = models.CharField(max_length=50, null=True, blank=True)
    material = models.CharField(max_length=255, null=True, blank=True)
    weight = models.PositiveIntegerField(null=True, blank=True)
    length = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    variant_rank = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.title

class ProductVariantInventoryItem(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item_id = models.CharField(max_length=255)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    required_quantity = models.PositiveIntegerField()
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"InventoryItem {self.inventory_item_id} for Variant {self.variant.title}"

class ProductVariantMoneyAmount(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    money_amount = models.ForeignKey('MoneyAmount', on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"MoneyAmount {self.money_amount.id} for Variant {self.variant.title}"

class PublishableApiKey(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='api_keys_created')
    revoked_by = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='api_keys_revoked')
    revoked_at = models.DateTimeField(null=True, blank=True)
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title

class PublishableApiKeySalesChannel(TimeStampedModel):
    sales_channel = models.ForeignKey('SalesChannel', on_delete=models.CASCADE)
    publishable_key = models.ForeignKey(PublishableApiKey, on_delete=models.CASCADE)
    # Assuming 'id' is a unique identifier for this relationship
    # If it's another UUID or specific field, adjust accordingly
    identifier = models.CharField(max_length=255, unique=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"APIKey {self.publishable_key.id} - SalesChannel {self.sales_channel.name}"

class Refund(TimeStampedModel):
    REASON_CHOICES = [
        ('customer_request', 'Customer Request'),
        ('damage', 'Damage'),
        # Add other reasons as needed
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    note = models.TextField(null=True, blank=True)
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)
    payment = models.ForeignKey('Payment', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Refund {self.id} - {self.amount} for Order {self.order.display_id}"

class Region(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    currency_code = models.CharField(max_length=10)
    tax_rate = models.FloatField()
    tax_code = models.CharField(max_length=50, null=True, blank=True)
    gift_cards_taxable = models.BooleanField(default=False)
    automatic_taxes = models.BooleanField(default=True)
    tax_provider = models.ForeignKey('TaxProvider', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.name

class RegionFulfillmentProvider(TimeStampedModel):
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    provider = models.ForeignKey('FulfillmentProvider', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('region', 'provider')

    def __str__(self):
        return f"Region {self.region.name} - FulfillmentProvider {self.provider.id}"

class RegionPaymentProvider(TimeStampedModel):
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    provider = models.ForeignKey('PaymentProvider', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('region', 'provider')

    def __str__(self):
        return f"Region {self.region.name} - PaymentProvider {self.provider.id}"

class Return(TimeStampedModel):
    STATUS_CHOICES = ReturnStatusEnum.choices

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    swap = models.ForeignKey('Swap', null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)
    shipping_data = JSONField(null=True, blank=True)
    refund_amount = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    received_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)
    claim_order = models.ForeignKey('ClaimOrder', null=True, blank=True, on_delete=models.SET_NULL)
    no_notification = models.BooleanField(default=False)
    location = models.ForeignKey('Location', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Return {self.id} - {self.status}"

class ReturnItem(TimeStampedModel):
    return_instance = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='return_items')
    item = models.ForeignKey(LineItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    is_requested = models.BooleanField(default=False)
    requested_quantity = models.PositiveIntegerField(null=True, blank=True)
    received_quantity = models.PositiveIntegerField(null=True, blank=True)
    reason = models.ForeignKey('ReturnReason', null=True, blank=True, on_delete=models.SET_NULL)
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"ReturnItem {self.id} for Return {self.return_instance.id}"

class ReturnReason(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    value = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    parent_return_reason = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='sub_reasons')

    def __str__(self):
        return self.label

class SalesChannel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    is_disabled = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class SalesChannelLocation(TimeStampedModel):
    sales_channel = models.ForeignKey(SalesChannel, on_delete=models.CASCADE)
    location = models.ForeignKey('Location', on_delete=models.CASCADE)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('sales_channel', 'location')

    def __str__(self):
        return f"SalesChannel {self.sales_channel.name} - Location {self.location.id}"


from django.db import models

class ShippingOption(TimeStampedModel):
    PRICE_TYPE_CHOICES = [
        ('FIXED', 'Fixed'),
        ('VARIABLE', 'Variable'),
        # Add actual enum choices here
    ]

    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    region = models.ForeignKey('Region', on_delete=models.CASCADE, related_name='shipping_options')
    profile = models.ForeignKey('ShippingProfile', on_delete=models.CASCADE, related_name='shipping_options')
    provider = models.ForeignKey('ShippingProvider', on_delete=models.CASCADE, related_name='shipping_options')
    price_type = models.CharField(max_length=50, choices=PRICE_TYPE_CHOICES)
    amount = models.IntegerField(null=True, blank=True)
    is_return = models.BooleanField()
    data = models.JSONField()
    deleted_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    admin_only = models.BooleanField()

    def __str__(self):
        return self.name


from django.db import models

class ShippingOptionRequirement(TimeStampedModel):
    REQUIREMENT_TYPE_CHOICES = [
        ('MIN', 'Minimum'),
        ('MAX', 'Maximum'),
        # Add actual enum choices here
    ]

    id = models.CharField(max_length=255, primary_key=True)
    shipping_option = models.ForeignKey('ShippingOption', on_delete=models.CASCADE, related_name='requirements')
    type = models.CharField(max_length=50, choices=REQUIREMENT_TYPE_CHOICES)
    amount = models.IntegerField()
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.type} requirement for {self.shipping_option.name}"


from django.db import models

class ShippingProfile(TimeStampedModel):
    PROFILE_TYPE_CHOICES = [
        ('STANDARD', 'Standard'),
        ('EXPRESS', 'Express'),
        # Add actual enum choices here
    ]

    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=PROFILE_TYPE_CHOICES)
    deleted_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.name

from django.db import models

class ShippingMethod(TimeStampedModel):
    id = models.CharField(max_length=255, primary_key=True)
    shipping_option = models.ForeignKey('ShippingOption', on_delete=models.CASCADE, related_name='shipping_methods')
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True, related_name='shipping_methods')
    cart = models.ForeignKey('Cart', on_delete=models.CASCADE, null=True, blank=True, related_name='shipping_methods')
    swap = models.ForeignKey('Swap', on_delete=models.CASCADE, null=True, blank=True, related_name='shipping_methods')
    return_ref = models.ForeignKey('Return', on_delete=models.CASCADE, null=True, blank=True, related_name='shipping_methods')
    price = models.IntegerField()
    data = models.JSONField()
    claim_order = models.ForeignKey('ClaimOrder', on_delete=models.CASCADE, null=True, blank=True, related_name='shipping_methods')
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ShippingMethod {self.id}"

from django.db import models

class ShippingMethodTaxLine(TimeStampedModel):
    id = models.CharField(max_length=255, primary_key=True)
    rate = models.FloatField()
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    shipping_method = models.ForeignKey('ShippingMethod', on_delete=models.CASCADE, related_name='tax_lines')

    def __str__(self):
        return f"TaxLine {self.id} for ShippingMethod {self.shipping_method.id}"

from django.db import models

class ShippingTaxRate(TimeStampedModel):
    shipping_option = models.ForeignKey('ShippingOption', on_delete=models.CASCADE, related_name='shipping_tax_rates')
    rate = models.ForeignKey('TaxRate', on_delete=models.CASCADE, related_name='shipping_tax_rates')
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ('shipping_option', 'rate')

    def __str__(self):
        return f"TaxRate {self.rate.name} for ShippingOption {self.shipping_option.name}"


from django.db import models

class Store(TimeStampedModel):
    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    default_currency = models.ForeignKey('Currency', on_delete=models.CASCADE, related_name='stores')
    swap_link_template = models.CharField(max_length=255, null=True, blank=True)
    payment_link_template = models.CharField(max_length=255, null=True, blank=True)
    invite_link_template = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    default_sales_channel = models.ForeignKey('SalesChannel', on_delete=models.SET_NULL, null=True, blank=True, related_name='default_for_stores')
    default_location = models.ForeignKey('Location', on_delete=models.SET_NULL, null=True, blank=True, related_name='default_for_stores')

    def __str__(self):
        return self.name

from django.db import models

class StoreCurrencies(models.Model):
    store = models.ForeignKey('Store', on_delete=models.CASCADE, related_name='currencies')
    currency = models.ForeignKey('Currency', on_delete=models.CASCADE, related_name='store_currencies')

    class Meta:
        unique_together = ('store', 'currency')

    def __str__(self):
        return f"{self.currency.code} for Store {self.store.name}"

from django.db import models



class Swap(TimeStampedModel):
    FULFILLMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('FULFILLED', 'Fulfilled'),
        ('CANCELED', 'Canceled'),
        # Add actual enum choices here
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        # Add actual enum choices here
    ]

    id = models.CharField(max_length=255, primary_key=True)
    fulfillment_status = models.CharField(max_length=50, choices=FULFILLMENT_STATUS_CHOICES)
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='swaps')
    difference_due = models.IntegerField(null=True, blank=True)
    shipping_address = models.ForeignKey('Address', on_delete=models.SET_NULL, null=True, blank=True, related_name='swaps')
    cart = models.ForeignKey('Cart', on_delete=models.SET_NULL, null=True, blank=True, related_name='swaps')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)
    no_notification = models.BooleanField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    allow_backorder = models.BooleanField()

    def __str__(self):
        return f"Swap {self.id} for Order {self.order.id}"


from django.db import models

class TaxProvider(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    is_installed = models.BooleanField()

    def __str__(self):
        return self.id

from django.db import models

class TaxRate(TimeStampedModel):
    id = models.CharField(max_length=255, primary_key=True)
    rate = models.FloatField(null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255)
    region = models.ForeignKey('Region', on_delete=models.CASCADE, related_name='tax_rates')
    metadata = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.name


from django.db import models

class TrackingLink(TimeStampedModel):
    id = models.CharField(max_length=255, primary_key=True)
    url = models.CharField(max_length=255, null=True, blank=True)
    tracking_number = models.CharField(max_length=255)
    fulfillment = models.ForeignKey('Fulfillment', on_delete=models.CASCADE, related_name='tracking_links')
    deleted_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"TrackingLink {self.tracking_number} for Fulfillment {self.fulfillment.id}"


from django.db import models

class StagedJob(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    event_name = models.CharField(max_length=255)
    data = models.JSONField()
    options = models.JSONField()

    def __str__(self):
        return f"StagedJob {self.id} - Event {self.event_name}"


from django.db import models

class User(TimeStampedModel):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('CUSTOMER', 'Customer'),
        ('SUPPLIER', 'Supplier'),
        # Add actual enum choices here
    ]

    id = models.CharField(max_length=255, primary_key=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    password_hash = models.CharField(max_length=255, null=True, blank=True)
    api_token = models.CharField(max_length=255, null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, null=True, blank=True)
    is_supplier = models.BooleanField(default=False)

    def __str__(self):
        return self.email
