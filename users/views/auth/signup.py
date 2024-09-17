from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from supabase import create_client
from gotrue.errors import AuthApiError
from user.models import UsersModel, Role, PartnerStore
import logging
import uuid

logger = logging.getLogger(__name__)

class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    full_name = serializers.CharField(required=True)
    username = serializers.CharField(required=False)
    role_id = serializers.UUIDField(required=False)
    store_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = UsersModel
        fields = ['email', 'password', 'full_name', 'username', 'role_id', 'store_url']


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
                
                # Associate user with a PartnerStore if store_url is provided
                self.associate_partner_store(django_user, serializer.validated_data.get('store_url'))
                
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
        user, created = UsersModel.objects.get_or_create(
            id=uuid.UUID(supabase_user.id),
            defaults={
                'email': validated_data['email'],
                'full_name': validated_data['full_name'],
                'username': validated_data.get('username', validated_data['email']),
                'roles_id': validated_data.get('role_id')
            }
        )
        if not created:
            user.full_name = validated_data['full_name']
            user.username = validated_data.get('username', validated_data['email'])
            user.roles_id = validated_data.get('role_id')
            user.save()
        return user

    def associate_partner_store(self, user, store_url=None):
        try:
            if store_url:
                store = get_object_or_404(PartnerStore, store_url=store_url)
                user.owned_stores.add(store)
                user.is_partner = True
                user.save()

        except PartnerStore.DoesNotExist:
            logger.error(f"Store with URL {store_url} does not exist")
            raise serializers.ValidationError(f"Store with URL {store_url} does not exist")
        except Exception as e:
            logger.error(f"Association with PartnerStore failed for user {user.id}: {str(e)}")
            raise

    def prepare_response(self, user, supabase_response):
        return {
            "message": "User created or updated successfully",
            "user_id": str(user.id),
            "username": user.username,
            "role": user.roles.name if user.roles else None,
            "access_token": supabase_response.session.access_token if supabase_response.session else None,
            "refresh_token": supabase_response.session.refresh_token if supabase_response.session else None,
        }