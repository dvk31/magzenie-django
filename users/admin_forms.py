# users/admin.py

from django.contrib import admin
from django.contrib.auth import get_user_model
from .admin_forms import SupabaseAdminAuthenticationForm

User = get_user_model()

class SupabaseAdminSite(admin.AdminSite):
    login_form = SupabaseAdminAuthenticationForm

admin_site = SupabaseAdminSite(name='supabase_admin')

@admin.register(User, site=admin_site)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser')
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ()

    fieldsets = (
        (None, {'fields': ('email',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'is_staff', 'is_superuser'),
        }),
    )

    def has_add_permission(self, request):
        return False  # Prevent adding users through admin

    def has_delete_permission(self, request, obj=None):
        return False  # Prevent deleting users through admin

    def has_change_permission(self, request, obj=None):
        return request.method in ['GET', 'HEAD']  # Allow viewing but not editing