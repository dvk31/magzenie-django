
from django.db import models
from django.contrib.postgres.fields import JSONField, ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import BaseModel
from django.db import models
from django.conf import settings
import json
import requests

import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import logging
from django.db.models import Q, Prefetch, F
from urllib.parse import quote_plus
from .user_methods_and_manager_methods import UserManagerMethods, UserMethods
from .user_roles import Role
from django.utils import timezone

logger = logging.getLogger(__name__)




class CustomUserManager(BaseUserManager, UserManagerMethods):
    pass

class UsersModel(AbstractBaseUser, BaseModel, PermissionsMixin):
    shopify_customer_id = models.CharField(max_length=50, null=True, blank=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    password = models.CharField(max_length=128, null=True, blank=True)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    partner_store_id = models.CharField(max_length=255, null=True, blank=True)
    owned_stores = models.ManyToManyField('PartnerStore', related_name='owners', blank=True)
    is_partner = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    roles = models.ManyToManyField('Role', blank=True)
    
    associated_kiosks = models.ManyToManyField('Kiosk', related_name='associated_users', blank=True)

    # Supabase-specific fields
    last_sign_in_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    @classmethod
    def is_username_available(cls, username):
        return cls.objects.is_username_available(username)
    def __str__(self):
        if self.username:
            return self.username
        elif hasattr(self, 'name') and self.name:
            return f"No User - {self.name}"
        else:
            return f"User {self.id}"

    profile = property(UserMethods.get_profile)








class PartnerStore(BaseModel):
    shopify_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    store_url = models.URLField(null=True, blank=True)
    logo_url = models.URLField(null=True, blank=True)
    kiosks = models.ManyToManyField('Kiosk', related_name='partner_stores', blank=True)

    
    def __str__(self):
        return f"PartnerStore: {self.name} (ID: {self.id}, Shopify ID: {self.shopify_id or 'Not synced'})"


class Product(BaseModel):
    shopify_id = models.CharField(max_length=255, unique=True)
    shopify_owner_reference = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    video_url = models.URLField(null=True, blank=True)
    thumbnail_url = models.URLField(null=True, blank=True)
    kiosk_video = models.FileField(upload_to='kiosk_videos/', null=True, blank=True)
    kiosk_collections = models.ManyToManyField('Collection', related_name='kiosk_products', blank=True)
    is_kiosk_active = models.BooleanField(default=True)
    kiosk_qr_codes = models.ManyToManyField('KioskQRCode', related_name='related_products', blank=True)

    
    @property
    def shopify_owner_reference(self):
        return f"gid://shopify/Customer/{self.owner.shopify_customer_id}"

    def __str__(self):
        return f"Product: {self.title} (ID: {self.id}, Shopify ID: {self.shopify_id})"




class Kiosk(BaseModel):
    shopify_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    kiosk_qr_code_url = models.URLField(null=True, blank=True)
    products = models.ManyToManyField('Product', related_name='kiosks', through='KioskQRCode')
    store = models.ForeignKey('PartnerStore', on_delete=models.CASCADE, related_name='owned_kiosks')
    is_active = models.BooleanField(default=True)
    collection = models.ForeignKey('Collection', on_delete=models.SET_NULL, null=True, blank=True, related_name='kiosks')
    pin_code = models.CharField(max_length=10, null=True, blank=True)
    qr_code_url = models.URLField(null=True, blank=True)
    shopify_location_id = models.CharField(max_length=255, null=True, blank=True)


    def __str__(self):
        return f"Kiosk: {self.name} (ID: {self.id}, Shopify ID: {self.shopify_id or 'Not synced'})"




class KioskQRCode(BaseModel):
    shopify_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    kiosk = models.ForeignKey('Kiosk', on_delete=models.CASCADE, related_name='kiosk_qr_codes')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='qr_codes')
    qr_code_url = models.URLField(unique=True, null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    
    class Meta:
        unique_together = ('kiosk', 'product')

    def __str__(self):
        return f"QR Code for {self.product.title} in {self.kiosk.name}"


class ScanEvent(BaseModel):
    shopify_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    session_id = models.CharField(max_length=255)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    kiosk = models.ForeignKey(Kiosk, on_delete=models.SET_NULL, null=True, blank=True, related_name='scan_events')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='scan_events')
    kiosk_qr_code = models.ForeignKey(KioskQRCode, on_delete=models.SET_NULL, null=True, related_name='scan_events')
    timestamp = models.DateTimeField(auto_now_add=True)
    device_type = models.CharField(max_length=100)
    user_agent = models.TextField()
    ip_address = models.GenericIPAddressField()

    def __str__(self):
        return f"Scan Event {self.id} - Product: {self.product.title} - Kiosk: {self.kiosk.name}"



class CustomerJourney(BaseModel):
    shopify_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='journeys')
    session_id = models.CharField(max_length=255, unique=True)
    initial_scan_event = models.ForeignKey('ScanEvent', on_delete=models.SET_NULL, null=True, related_name='initiated_journeys')
    last_interaction = models.DateTimeField(auto_now=True)
    conversion_status = models.CharField(max_length=50, default='initial_scan')
    associated_order = models.CharField(max_length=255, null=True, blank=True)
    
    # You might want to store the journey data as JSON
    interactions = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Customer Journey: {self.session_id} - Status: {self.conversion_status}"

    class Meta:
        verbose_name_plural = "Customer Journeys"

    def add_interaction(self, interaction_type, details):
        """
        Add a new interaction to the journey.
        """
        if not self.interactions:
            self.interactions = {}
        
        timestamp = timezone.now().isoformat()
        if interaction_type not in self.interactions:
            self.interactions[interaction_type] = []
        
        self.interactions[interaction_type].append({
            'timestamp': timestamp,
            'details': details
        })
        self.save()

    def update_conversion_status(self, new_status):
        """
        Update the conversion status of the journey.
        """
        self.conversion_status = new_status
        self.save()

    @property
    def duration(self):
        """
        Calculate the duration of the journey so far.
        """
        if self.initial_scan_event:
            return self.last_interaction - self.initial_scan_event.timestamp
        return None

class StoreLocation(BaseModel):
    partner_store = models.ForeignKey(PartnerStore, on_delete=models.CASCADE, related_name='locations')
    shopify_location_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    address = models.TextField()

    def __str__(self):
        return f"{self.partner_store.name} - {self.name}"



class Collection(BaseModel):
    shopify_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    kiosk = models.ForeignKey('Kiosk', on_delete=models.SET_NULL, null=True, blank=True, related_name='collections')
    sort_order = models.IntegerField(null=True, blank=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    products = models.ManyToManyField('Product', related_name='collections', blank=True)
    display_start_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Collection: {self.name} (ID: {self.id}, Shopify ID: {self.shopify_id or 'Not synced'})"
# In models.py
from django.db import models

