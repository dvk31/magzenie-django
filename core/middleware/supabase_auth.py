# middleware.py
from django.contrib.auth import authenticate
from django.utils.functional import SimpleLazyObject
from django.utils.deprecation import MiddlewareMixin

class SupabaseAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not hasattr(request, 'user'):
            return

        # Check if it's an admin URL
        if request.path.startswith('/admin/'):
            # For admin URLs, don't use token authentication
            return

        token = request.META.get('HTTP_AUTHORIZATION', '').split('Bearer ')[-1]
        if token:
            request.user = SimpleLazyObject(lambda: authenticate(request, token=token))