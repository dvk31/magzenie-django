# core/services.py

from django.conf import settings
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

class SupabaseService:
    def __init__(self):
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    def delete_user(self, user_id):
        try:
            response = self.client.auth.admin.delete_user(user_id)
            logger.info(f"User {user_id} deleted from Supabase")
            return True
        except Exception as e:
            logger.error(f"Error deleting user {user_id} from Supabase: {str(e)}")
            return False

    def get_user(self, user_id):
        try:
            user = self.client.auth.admin.get_user(user_id)
            return user
        except Exception as e:
            logger.error(f"Error fetching user {user_id} from Supabase: {str(e)}")
            return None

    # Add more Supabase-related methods as needed