# core/base_models.py

# core/models.py

import uuid
from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import JSONField  # Use if Django < 3.1

# For Django 3.1 and above, you can use the built-in JSONField
try:
    from django.db.models import JSONField as BuiltInJSONField
except ImportError:
    BuiltInJSONField = JSONField


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

# Add other enums similarly...


# ==========================
# Abstract Base Models
# ==========================

# core/models.py

from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import JSONField  # Use if Django < 3.1
from .managers import SoftDeleteManager

try:
    from django.db.models import JSONField as BuiltInJSONField
except ImportError:
    from django.contrib.postgres.fields import JSONField
    BuiltInJSONField = JSONField


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    'created_at', 'updated_at', and 'deleted_at' fields.
    """
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    metadata = BuiltInJSONField(null=True, blank=True)  # Use JSONField for jsonb

    objects = SoftDeleteManager()  # Default manager excludes soft-deleted records
    all_objects = models.Manager()  # Includes all records

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """
        Override the delete method to perform a soft delete.
        """
        self.deleted_at = timezone.now()
        self.save()


class UUIDModel(TimeStampedModel):
    """
    An abstract base class model that uses a UUID as the primary key.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

