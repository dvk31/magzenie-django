from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from supabase import create_client, Client
from django.conf import settings
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class SupabaseAuthBackend(ModelBackend):
    def __init__(self):
        self.supabase = self._initialize_supabase_client()

    def _initialize_supabase_client(self):
        try:
            project_url = settings.SUPABASE_URL
            api_key = settings.SUPABASE_KEY
            
            if not project_url or not api_key:
                logger.error("SUPABASE_URL or SUPABASE_KEY not set in settings")
                return None
            
            return create_client(project_url, api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            return None

    def authenticate(self, request, username=None, password=None, token=None, **kwargs):
        # For admin login, use username and password
        if username and password:
            return self._authenticate_with_credentials(username, password)
        
        # For API requests, use token
        if token:
            return self._authenticate_with_token(token)
        
        return None

    def _authenticate_with_credentials(self, username, password):
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

    def _authenticate_with_token(self, token):
        if not self.supabase:
            logger.error("Supabase client is not initialized")
            return None

        try:
            return self._get_or_create_user(token)
        except Exception as e:
            logger.error(f"Token authentication failed: {str(e)}", exc_info=True)
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.warning(f"User with id {user_id} does not exist")
            return None

    def _get_or_create_user(self, token):
            try:
                user_data = self.supabase.auth.get_user(token)
                if not user_data or 'id' not in user_data:
                    logger.error("Invalid user data returned from Supabase")
                    return None
                
                supabase_uid = user_data['id']
                email = user_data.get('email')
                
                user, created = User.objects.get_or_create(
                    id=supabase_uid,
                    defaults={'email': email, 'username': email}
                )
                
                if created:
                    logger.info(f"New user created with Supabase ID: {supabase_uid}")
                return user
            except Exception as e:
                logger.error(f"Error in _get_or_create_user: {str(e)}")
                return None