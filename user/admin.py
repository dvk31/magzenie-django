from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    UsersModel, Role, PartnerStore, Product, Kiosk, KioskQRCode, ScanEvent,
    CustomerJourney, StoreLocation, Collection
)

class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

class PartnerStoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'shopify_id', 'owner', 'store_url')
    search_fields = ('name', 'shopify_id', 'owner__username')

class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'shopify_id', 'price', 'is_kiosk_active')
    list_filter = ('is_kiosk_active',)
    search_fields = ('title', 'shopify_id')

class KioskQRCodeInline(admin.TabularInline):
    model = KioskQRCode
    extra = 1

class KioskAdmin(admin.ModelAdmin):
    list_display = ('name', 'shopify_id', 'store', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'shopify_id')
    inlines = [KioskQRCodeInline]

class ScanEventAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'kiosk', 'product', 'customer')
    list_filter = ('timestamp', 'kiosk')
    search_fields = ('kiosk__name', 'product__title', 'customer__username')

class CustomerJourneyAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'customer', 'conversion_status', 'last_interaction')
    list_filter = ('conversion_status',)
    search_fields = ('session_id', 'customer__username')

class StoreLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'partner_store', 'shopify_location_id')
    search_fields = ('name', 'partner_store__name', 'shopify_location_id')

class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'shopify_id', 'kiosk', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'shopify_id')

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'full_name', 'is_partner', 'is_active', 'is_staff')
    list_filter = ('is_partner', 'is_active', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email', 'full_name', 'first_name', 'last_name', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login',)}),  # Removed 'date_joined'
        ('Additional info', {'fields': ('shopify_customer_id', 'partner_store_id', 'is_partner', 'roles')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    search_fields = ('username', 'email', 'full_name')
    ordering = ('username',)


admin.site.register(KioskQRCode)
admin.site.register(UsersModel, CustomUserAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(PartnerStore, PartnerStoreAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Kiosk, KioskAdmin)
admin.site.register(ScanEvent, ScanEventAdmin)
admin.site.register(CustomerJourney, CustomerJourneyAdmin)
admin.site.register(StoreLocation, StoreLocationAdmin)
admin.site.register(Collection, CollectionAdmin)