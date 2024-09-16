import logging
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)

class TokenTranslationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self.is_supabase_request(request):
            try:
                self.translate_token_for_supabase(request)
            except AuthenticationFailed as e:
                logger.error(f"Token translation error: {str(e)}")
                # Handle the error, e.g., return a 401 response or raise an exception
            except Exception as e:
                logger.error(f"Unexpected error during token translation: {str(e)}")
                # Handle unexpected errors, perhaps returning a 500 response or raising an exception

        return self.get_response(request)

    def is_supabase_request(self, request):
        return '/supabase/' in request.path

    def translate_token_for_supabase(self, request):
        auth_header = get_authorization_header(request).decode('utf-8')
        
        if not auth_header or 'token' not in auth_header.lower():
            raise AuthenticationFailed('No valid token provided.')
        
        drf_token_key = auth_header.split()[1]
        supabase_token = self.get_supabase_token(drf_token_key)
        
        if not supabase_token:
            raise AuthenticationFailed('Token translation failed.')
        
        request.headers['Authorization'] = f'Bearer {supabase_token}'

    def get_supabase_token(self, drf_token_key):
        try:
            token_mapping = TokenMapping.objects.get(drf_token__key=drf_token_key)
            return token_mapping.supabase_token
        except TokenMapping.DoesNotExist:
            logger.warning(f"DRF token {drf_token_key} does not have a corresponding Supabase token.")
            return None
        except Exception as e:
            logger.error(f"Unexpected error when fetching Supabase token for DRF token {drf_token_key}: {str(e)}")
            return None
