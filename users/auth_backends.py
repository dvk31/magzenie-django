#users/auth_backends.py

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from supabase import create_client, Client
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

# users/auth_backends.py
import logging
from django.contrib.auth.backends import ModelBackend
from supabase import create_client, Client
from django.conf import settings

logger = logging.getLogger(__name__)

class SupabaseAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        logger.debug(f"SupabaseAuthBackend.authenticate called for user: {username}")
        
        if username is None or password is None:
            logger.debug("Username or password is None, returning None")
            return None

        try:
            supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            logger.debug(f"Attempting to sign in with Supabase for user: {username}")
            response = supabase.auth.sign_in_with_password({"email": username, "password": password})
            logger.debug(f"Supabase sign_in_with_password response: {response}")
            
            if response.user:
                logger.debug(f"Supabase authentication successful for user: {username}")
                logger.debug(f"Supabase user data: {response.user}")
                user, created = User.objects.get_or_create(
                    email=username,
                    defaults={'username': username}
                )
                if created:
                    logger.debug(f"Created new Django user for: {username}")
                else:
                    logger.debug(f"Retrieved existing Django user for: {username}")
                
                # Update only non-generated fields
                user.is_super_admin = response.user.app_metadata.get('role') == 'supabase_admin'
                # Add any other fields you want to update here, but avoid generated columns
                
                user.save(update_fields=['is_super_admin'])  # Only update specific fields
                logger.debug(f"User authenticated: {user.email}, is_super_admin={user.is_super_admin}")
                return user
            else:
                logger.debug(f"Supabase authentication failed for user: {username}")
                logger.debug(f"Supabase response details: {response}")
        except Exception as e:
            logger.exception(f"Error during Supabase authentication: {str(e)}")
            logger.debug(f"Exception type: {type(e).__name__}")
            logger.debug(f"Exception args: {e.args}")
            logger.debug(f"Exception details: {e.__dict__}")

        logger.debug(f"SupabaseAuthBackend.authenticate returning None for user: {username}")
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def has_perm(self, user_obj, perm, obj=None):
        if user_obj.is_anonymous:
            return False
        return user_obj.is_super_admin

    def has_module_perms(self, user_obj, app_label):
        logger.debug(f"Checking module permissions for user: {user_obj}")
        if user_obj.is_anonymous:
            logger.debug("User is anonymous, returning False")
            return False
        return user_obj.is_super_admin