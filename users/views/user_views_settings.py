
from django.utils import timezone
from datetime import timedelta
import logging
import traceback
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser

from notifications.models.notifications_model import NotificationPreferences
from users.models import UserProfile
from payments.models import Subscription, SubscriptionPlan, PaymentMethod, Address

from .serializers import (
    UserSettingsSerializer,
    UserProfileSerializer,
    SubscriptionSerializer,
    PaymentMethodSerializer,
    AddressSerializer,
    NotificationPreferencesSerializer,
    UpdateUserSettingsProfileRequestSerializer,
    UpdateUserSettingsPasswordRequestSerializer,
    AddPaymentMethodSerializer,
    AddAddressSerializer,
    UpdateUserSettingsResponseSerializer,
    ErrorResponseSerializer
)

# Import the schemas
from .schemas import user_settings_get_schema, user_settings_put_patch_schema

# Initialize logger
logger = logging.getLogger(__name__)


class UserSettingsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='user/settings')
    def user_settings(self, request):
        """
        Handle GET, PUT, and PATCH requests for user settings.
        """
        if request.method == 'GET':
            return self.get_user_settings(request)
        elif request.method in ['PUT', 'PATCH']:
            return self.update_user_settings(request)
        else:
            return Response(
                {"success": False, "message": "Method not allowed."},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

    # Apply the schema to the get_user_settings method
    @user_settings_get_schema
    def get_user_settings(self, request):
        try:
            user = request.user

            # Get or create notification preferences
            notification_preferences, _ = NotificationPreferences.objects.get_or_create(user=user)

            # Get or create user profile
            user_profile, _ = UserProfile.objects.get_or_create(user=user)

            # Get or create subscription
            subscription = Subscription.objects.filter(user=user).first()
            if not subscription:
                # If no subscription exists, create a default one
                default_plan, _ = SubscriptionPlan.objects.get_or_create(
                    name='Free',
                    defaults={
                        'price': 0.0,
                        'duration_months': 1,
                        'description': 'Free plan'
                    }
                )
                subscription = Subscription.objects.create(
                    user=user,
                    plan=default_plan,
                    end_date=timezone.now().date() + timedelta(days=30),
                    active=True
                )

            user_settings = {
                "profile": UserProfileSerializer(user_profile).data,
                "subscription": SubscriptionSerializer(subscription).data,
                "payment_methods": PaymentMethodSerializer(user.payment_methods.all(), many=True).data,
                "addresses": AddressSerializer(user.addresses.all(), many=True).data,
                "notification_preferences": NotificationPreferencesSerializer(notification_preferences).data
            }

            serializer = UserSettingsSerializer(data=user_settings)
            serializer.is_valid(raise_exception=True)
            logger.info(f"User settings retrieved for: {user.email}")
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving user settings: {str(e)}")
            logger.debug(traceback.format_exc())
            return Response(
                {"success": False, "message": "Failed to retrieve user settings."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # Apply the schema to the update_user_settings method
    @user_settings_put_patch_schema
    def update_user_settings(self, request):
        try:
            user = request.user
            data = request.data

            # If the data is not a dict (e.g., if it's a QueryDict from form data), convert it
            if not isinstance(data, dict):
                data = dict(data.items())

            # Handle profile update
            if 'profile' in data or 'full_name' in data:
                profile_data = data.get('profile', {})
                if 'full_name' in data:
                    profile_data['full_name'] = data['full_name']

                profile_serializer = UpdateUserSettingsProfileRequestSerializer(
                    data=profile_data, partial=True
                )
                if profile_serializer.is_valid():
                    profile = user.userprofile
                    for key, value in profile_serializer.validated_data.items():
                        setattr(profile, key, value)
                    profile.save()
                    logger.info(f"User profile updated for: {user.email}")
                else:
                    return Response(profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Handle password update
            if 'current_password' in data and 'new_password' in data:
                password_serializer = UpdateUserSettingsPasswordRequestSerializer(data=data)
                if password_serializer.is_valid():
                    password_data = password_serializer.validated_data
                    if not user.check_password(password_data['current_password']):
                        logger.warning(f"Password update failed due to incorrect current password for user: {user.email}")
                        return Response(
                            {"success": False, "message": "Current password is incorrect."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    user.set_password(password_data['new_password'])
                    user.save()
                    logger.info(f"User password updated for: {user.email}")
                else:
                    return Response(password_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Handle payment method update
            if 'payment_method' in data:
                payment_serializer = AddPaymentMethodSerializer(data=data)
                if payment_serializer.is_valid():
                    payment_data = payment_serializer.validated_data
                    PaymentMethod.objects.create(user=user, **payment_data['payment_method'])
                    logger.info(f"Payment method added for user: {user.email}")
                else:
                    return Response(payment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Handle address update
            if 'address' in data:
                address_serializer = AddAddressSerializer(data=data)
                if address_serializer.is_valid():
                    address_data = address_serializer.validated_data['address']
                    Address.objects.create(user=user, **address_data)
                    logger.info(f"Address added for user: {user.email}")
                else:
                    return Response(address_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            if not any(key in data for key in ['profile', 'full_name', 'current_password', 'payment_method', 'address']):
                logger.warning(f"Update settings called with invalid data by user: {user.email}")
                return Response(
                    {"success": False, "message": "Invalid update parameters."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({
                "success": True,
                "message": "Settings updated successfully."
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating user settings: {str(e)}")
            logger.debug(traceback.format_exc())
            return Response(
                {"success": False, "message": "Failed to update settings due to an unexpected error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )