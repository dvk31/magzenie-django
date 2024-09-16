# users/backends.py
from django.contrib.auth.backends import ModelBackend
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
import logging

from .models import UsersModel
from django.contrib.auth.backends import ModelBackend
from .models import UsersModel

logger = logging.getLogger(__name__)
class PhoneNumberAuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, **kwargs):
        try:
            user = UsersModel.objects.get(phone_number=username)
            return user
        except UsersModel.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return UsersModel.objects.get(pk=user_id)
        except UsersModel.DoesNotExist:
            return None

    def authenticate_by_phone(self, phone_number):
        try:
            user = UsersModel.objects.get(phone_number=phone_number)
            return user
        except UsersModel.DoesNotExist:
            return None


class PhoneNumberAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        phone_number = request.data.get("phone_number")
        if not phone_number:
            return None

        backend = PhoneNumberAuthenticationBackend()
        user = backend.authenticate_by_phone(phone_number)
        if user is None:
            raise AuthenticationFailed("No such user")

        return (user, None)  # authentication successful


# users/backends.py



logger = logging.getLogger(__name__)

class EmailAuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get('email', username)
        try:
            user = UsersModel.objects.get(email=email)
            if user.check_password(password):
                if not user.is_active:
                    logger.error(f"User account with email {email} is inactive.")
                    return None
                return user
            else:
                logger.error(f"Password check failed for user with email: {email}")
        except UsersModel.DoesNotExist:
            logger.error(f"User with email {email} does not exist.")
        return None


    def has_perm(self, user_obj, perm, obj=None):
        has_perm = super().has_perm(user_obj, perm, obj)
        if has_perm:
            return True
        elif obj is not None:
            # This part will only be used for object-level checks, not in our API view
            if hasattr(obj, 'owner'):
                return obj.owner == user_obj
            elif hasattr(obj, 'user'):
                return obj.user == user_obj
        return False

    def get_user(self, user_id):
        try:
            return UsersModel.objects.get(pk=user_id)
        except UsersModel.DoesNotExist:
            return None