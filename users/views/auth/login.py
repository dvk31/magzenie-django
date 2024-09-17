from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiResponse
import logging
from django.conf import settings
from supabase import create_client, Client
from gotrue.errors import AuthApiError
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

logger = logging.getLogger(__name__)

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful"),
            400: OpenApiResponse(description="Bad request"),
            401: OpenApiResponse(description="Invalid credentials"),
            429: OpenApiResponse(description="Too many requests"),
            500: OpenApiResponse(description="Internal server error"),
        },
        description="Log in a user",
        tags=["Authentication"]
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            # Initialize Supabase client
            supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

            # Attempt to sign in the user
            auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})

            # Extract user data and session from the response
            user = auth_response.user
            session = auth_response.session

            if not user or not session:
                return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

            # Fetch the corresponding Django user
            try:
                django_user = User.objects.get(id=user.id)
            except User.DoesNotExist:
                logger.error(f"Django user not found for Supabase user ID: {user.id}")
                return Response({"error": "User account not properly set up"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            response_data = {
                "message": "Login successful",
                "user_id": django_user.id,
                "username": django_user.username,
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except AuthApiError as e:
            if "Invalid login credentials" in str(e):
                return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)
            elif "Email rate limit exceeded" in str(e):
                return Response({"error": "Too many login attempts. Please try again later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            else:
                logger.error(f"AuthApiError during login: {str(e)}")
                return Response({"error": "An error occurred during login"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error in user login: {str(e)}", exc_info=True)
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)