# hellogpt/middleware/supa_middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import authenticate, login
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import authenticate, login

class SupabaseAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        token = request.headers.get('Authorization')
        if token and token.startswith('Bearer '):
            token = token.split('Bearer ')[1]
            user = authenticate(request, supabase_token=token)
            if user:
                request.user = user


    def _is_excluded_path(self, path):
        # Add paths that should not go through this authentication process
        excluded_paths = getattr(settings, 'SUPABASE_AUTH_EXCLUDED_PATHS', [])
        return any(path.startswith(excluded) for excluded in excluded_paths)