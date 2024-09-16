# core/common/authentication.py
import logging
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

# Set up logging
logger = logging.getLogger(__name__)

class CustomTokenAuthentication(TokenAuthentication):
    keyword = "Bearer"  # Set 'Bearer' keyword

    def authenticate_credentials(self, key):
        logger.info(f"Attempting to authenticate with token: {key}")
        try:
            token = Token.objects.select_related('user').get(key=key)
            logger.info("Token found and valid.")
        except Token.DoesNotExist:
            logger.warning(f"Invalid token provided: {key}")
            raise AuthenticationFailed("Invalid token.")

        if not token.user.is_active:
            logger.warning(f"Inactive user attempted to authenticate: {token.user}")
            raise AuthenticationFailed("User not active.")

        # Optional: Check token expiry
        token_expiry = getattr(settings, 'TOKEN_EXPIRY_DAYS', None)
        if token_expiry is not None:
            expiry_date = token.created + timedelta(days=token_expiry)
            if timezone.now() > expiry_date:
                logger.warning(f"Token expired for user: {token.user}")
                raise AuthenticationFailed("Token has expired.")

        return token.user, token