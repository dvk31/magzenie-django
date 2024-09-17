# users/views/users_view.py
from django.utils import timezone
from datetime import timedelta
import logging
import traceback
from django.core.exceptions import ObjectDoesNotExist
from notifications.models.notifications_model import NotificationPreferences
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
)

from .serializers import (
    RegistrationRequestSerializer,
    RegistrationResponseSerializer,
    LoginRequestSerializer,
    LoginResponseSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmationSerializer,
    LogoutResponseSerializer,
    UserSettingsSerializer,
    UserProfileSerializer,
    UpdateUserSettingsProfileRequestSerializer,
    UpdateUserSettingsPasswordRequestSerializer,
    AddPaymentMethodSerializer,
    AddAddressSerializer,
    UpdateUserSettingsResponseSerializer,
    PaymentMethodSerializer,  # Ensure these serializers are imported
    AddressSerializer,
    NotificationPreferencesSerializer,
    ErrorResponseSerializer, 
    SubscriptionSerializer # Serializer for error responses
)
from users.models import UserProfile 

from payments.models import (
    Payment,
    PromoCode,
    SubscriptionPlan,
    Subscription,
    Address,
    PaymentMethod
)

# Initialize logger
logger = logging.getLogger(__name__)

User = get_user_model()

class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @extend_schema(
        description="Register a new user with email and password.",
        request=RegistrationRequestSerializer,
        responses={
            201: RegistrationResponseSerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                'Example Request',
                value={
                    "email": "john.doe@example.com",
                    "password": "StrongPassword123!",
                    "full_name": "John Doe"
                },
                request_only=True
            ),
            OpenApiExample(
                'Example Response',
                value={
                    "success": True,
                    "user_id": 1,
                    "message": "Registration successful."
                },
                response_only=True
            )
        ]
    )
    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        try:
            serializer = RegistrationRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            if User.objects.filter(email=data['email']).exists():
                logger.warning(f"Registration attempt with existing email: {data['email']}")
                return Response(
                    {"success": False, "message": "Email already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.create_user(
                email=data['email'],
                password=data['password']
            )
            user.profile.full_name = data['full_name']
            user.profile.save()

            response_serializer = RegistrationResponseSerializer({
                "success": True,
                "user_id": user.id,
                "message": "Registration successful."
            })
            logger.info(f"User registered successfully: {user.email}")
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error during registration: {str(e)}")
            logger.debug(traceback.format_exc())
            return Response(
                {"success": False, "message": "Registration failed due to an unexpected error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        description="Authenticate user with email and password.",
        request=LoginRequestSerializer,
        responses={
            200: LoginResponseSerializer,
            401: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                'Example Request',
                value={
                    "email": "john.doe@example.com",
                    "password": "StrongPassword123!"
                },
                request_only=True
            ),
            OpenApiExample(
                'Example Response',
                value={
                    "success": True,
                    "user_id": 1,
                    "token": "jwt.token.here",
                    "message": "Login successful."
                },
                response_only=True
            )
        ]
    )
    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        try:
            serializer = LoginRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            user = authenticate(username=data['email'], password=data['password'])
            if user is not None:
                refresh = RefreshToken.for_user(user)
                response_serializer = LoginResponseSerializer({
                    "success": True,
                    "user_id": user.id,
                    "token": str(refresh.access_token),
                    "message": "Login successful."
                })
                logger.info(f"User logged in successfully: {user.email}")
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                logger.warning(f"Invalid login attempt for email: {data['email']}")
                return Response(
                    {"success": False, "message": "Invalid credentials."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            logger.debug(traceback.format_exc())
            return Response(
                {"success": False, "message": "Login failed due to an unexpected error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        description="Logout the authenticated user.",
        responses={
            200: LogoutResponseSerializer,
            500: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                'Example Response',
                value={
                    "success": True,
                    "message": "Logout successful."
                },
                response_only=True
            )
        ]
    )
    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self, request):
        try:
            # For JWT, logout is handled on client side by discarding the token
            # Optionally, implement token blacklisting here
            response_serializer = LogoutResponseSerializer({
                "success": True,
                "message": "Logout successful."
            })
            logger.info(f"User logged out: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            logger.debug(traceback.format_exc())
            return Response(
                {"success": False, "message": "Logout failed due to an unexpected error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PasswordResetViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @extend_schema(
        description="Request a password reset by providing the user's email.",
        request=PasswordResetRequestSerializer,
        responses={
            200: {
                "success": True,
                "message": "Password reset instructions sent to email."
            },
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                'Example Request',
                value={
                    "email": "john.doe@example.com"
                },
                request_only=True
            ),
            OpenApiExample(
                'Example Response',
                value={
                    "success": True,
                    "message": "Password reset instructions sent to email."
                },
                response_only=True
            )
        ]
    )
    @action(detail=False, methods=['post'], url_path='password-reset/request')
    def password_reset_request(self, request):
        try:
            serializer = PasswordResetRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            user = User.objects.filter(email=data['email']).first()
            if user:
                # Implement sending password reset email with token
                # For demonstration, assume it's successful
                logger.info(f"Password reset requested for email: {user.email}")
                # TODO: Integrate with email service to send reset link
            else:
                logger.warning(f"Password reset requested for non-existent email: {data['email']}")

            return Response({
                "success": True,
                "message": "Password reset instructions sent to email."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error during password reset request: {str(e)}")
            logger.debug(traceback.format_exc())
            return Response(
                {"success": False, "message": "Password reset request failed due to an unexpected error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        description="Confirm password reset by providing the reset token and new password.",
        request=PasswordResetConfirmationSerializer,
        responses={
            200: {
                "success": True,
                "message": "Password reset successful."
            },
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                'Example Request',
                value={
                    "token": "reset-token-here",
                    "new_password": "NewStrongPassword123!",
                    "confirm_password": "NewStrongPassword123!"
                },
                request_only=True
            ),
            OpenApiExample(
                'Example Response',
                value={
                    "success": True,
                    "message": "Password reset successful."
                },
                response_only=True
            )
        ]
    )
    @action(detail=False, methods=['post'], url_path='password-reset/confirm')
    def password_reset_confirm(self, request):
        try:
            serializer = PasswordResetConfirmationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            if data['new_password'] != data['confirm_password']:
                logger.warning("Password reset attempt with mismatched passwords.")
                return Response(
                    {"success": False, "message": "Passwords do not match."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verify token and retrieve user
            # TODO: Implement actual token verification logic
            # For demonstration, assume token is valid and retrieve user
            user = User.objects.filter(email="john.doe@example.com").first()  # Placeholder
            if not user:
                logger.warning("Password reset attempt for non-existent user.")
                return Response(
                    {"success": False, "message": "Invalid token or user does not exist."},
                    status=status.HTTP_404_NOT_FOUND
                )

            user.set_password(data['new_password'])
            user.save()
            logger.info(f"Password reset successful for user: {user.email}")

            return Response({
                "success": True,
                "message": "Password reset successful."
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error during password reset confirmation: {str(e)}")
            logger.debug(traceback.format_exc())
            return Response(
                {"success": False, "message": "Password reset failed due to an unexpected error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
