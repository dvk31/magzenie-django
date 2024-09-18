from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.conf import settings
from supabase import create_client
from gotrue.errors import AuthApiError
from users.models import User, UserProfile
import logging
import uuid

logger = logging.getLogger(__name__)

class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    full_name = serializers.CharField(required=True)
    username = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ['email', 'password', 'full_name', 'username']

class UserSignupView(APIView):
    permission_classes = [AllowAny]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    @extend_schema(
        request=UserSignupSerializer,
        responses={
            201: OpenApiResponse(description="User created or updated successfully"),
            400: OpenApiResponse(description="Bad request"),
            429: OpenApiResponse(description="Too many requests"),
            500: OpenApiResponse(description="Internal server error"),
        },
        description="Sign up a new user or update existing user",
        tags=["Authentication"]
    )
    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                supabase_response = self.get_or_create_supabase_user(serializer.validated_data)
                django_user = self.get_or_create_django_user(supabase_response.user, serializer.validated_data)
                
                response_data = self.prepare_response(django_user, supabase_response)
                return Response(response_data, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in user signup: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred during signup"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_or_create_supabase_user(self, validated_data):
        try:
            return self.supabase.auth.sign_up({
                "email": validated_data['email'],
                "password": validated_data['password'],
            })
        except AuthApiError as e:
            if "User already registered" in str(e):
                return self.supabase.auth.sign_in_with_password({
                    "email": validated_data['email'],
                    "password": validated_data['password'],
                })
            else:
                raise

    def get_or_create_django_user(self, supabase_user, validated_data):
        # First, get or create the Users instance (Supabase user)
        supabase_user_instance, _ = Users.objects.get_or_create(
            id=supabase_user.id,
            defaults={
                'email': validated_data['email'],
                # Add other fields from Supabase user data as needed
            }
        )

        # Now, get or create the User instance (Django user)
        user, created = User.objects.get_or_create(
            supabase_user=supabase_user_instance,
            defaults={
                'email': validated_data['email'],
                'username': validated_data.get('username', User.objects.generate_unique_username()),
            }
        )

        if not created:
            user.username = validated_data.get('username', user.username)
            user.save()

        # Update or create UserProfile
        UserProfile.objects.update_or_create(
            user=user,
            defaults={'full_name': validated_data['full_name']}
        )

        return user

    def prepare_response(self, user, supabase_response):
        return {
            "message": "User created or updated successfully",
            "user_id": str(user.id),
            "supabase_user_id": str(user.supabase_user.id),  # Add this line
            "username": user.username,
            "access_token": supabase_response.session.access_token if supabase_response.session else None,
            "refresh_token": supabase_response.session.refresh_token if supabase_response.session else None,
        }