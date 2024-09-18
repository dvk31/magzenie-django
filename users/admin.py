from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from users.models import UserProfile

User = get_user_model()

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'id', 'role', 'is_active', 'is_staff', 'is_superuser', 'last_sign_in_at')
    list_filter = ('role', 'is_sso_user', 'is_anonymous', 'is_super_admin')
    search_fields = ('email', 'id', 'phone')
    ordering = ('email',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_sign_in_at', 'encrypted_password', 
                       'is_active', 'is_staff', 'is_superuser')
    inlines = [UserProfileInline]

    fieldsets = (
        (None, {'fields': ('email', 'phone', 'role')}),
        (_('Permissions'), {'fields': ('is_super_admin', 'is_sso_user', 'is_anonymous')}),
        (_('Metadata'), {'fields': ('raw_app_meta_data', 'raw_user_meta_data')}),
        (_('Important dates'), {'fields': ('last_sign_in_at', 'created_at', 'updated_at', 'banned_until')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'role'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('email',)
        return self.readonly_fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.is_super_admin

    def has_view_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.is_super_admin

    def has_change_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.is_super_admin

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio', 'birth_date', 'location', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('user__email', 'location')
    list_filter = ('is_staff', 'is_superuser', 'is_active')

    fieldsets = (
        (None, {'fields': ('user', 'bio', 'birth_date', 'location')}),
        (_('Permissions'), {'fields': ('is_staff', 'is_superuser', 'is_active')}),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.is_super_admin

    def has_view_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.is_super_admin

    def has_change_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.is_super_admin

# Customize admin site
admin.site.site_header = 'Magzenie Admin Portal'
admin.site.site_title = 'Magzenie Admin'
admin.site.index_title = 'Welcome to Magzenie Admin'