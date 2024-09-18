# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from supabase import create_client, Client
from django.conf import settings
from users.models import User
from django.contrib.auth import login
from rest_framework.authtoken.models import Token
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from rest_framework import serializers

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Serializers
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class LoginResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    token = serializers.CharField()
    supabase_access_token = serializers.CharField()
    supabase_refresh_token = serializers.CharField()

class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

class RefreshTokenResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()

class LogoutResponseSerializer(serializers.Serializer):
    message = serializers.CharField()

class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class SignupResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user_id = serializers.CharField()

# Views
class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200: LoginResponseSerializer},
        description="Login with email and password",
        tags=["Authentication"]
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            user, _ = User.objects.get_or_create(email=email)
            login(request, user)
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "message": "Login successful",
                "token": token.key,
                "supabase_access_token": response.session.access_token,
                "supabase_refresh_token": response.session.refresh_token
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RefreshTokenSerializer,
        responses={200: RefreshTokenResponseSerializer},
        description="Refresh the access token",
        tags=["Authentication"]
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data['refresh_token']

        try:
            response = supabase.auth.refresh_session(refresh_token)
            return Response({
                "message": "Token refreshed",
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    @extend_schema(
        responses={200: LogoutResponseSerializer},
        description="Logout the user",
        tags=["Authentication"]
    )
    def post(self, request):
        try:
            supabase.auth.sign_out()
            request.user.auth_token.delete()
            return Response({"message": "Logout successful"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SignupView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=SignupSerializer,
        responses={201: SignupResponseSerializer},
        description="Sign up a new user",
        tags=["Authentication"]
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            response = supabase.auth.sign_up({"email": email, "password": password})
            return Response({
                "message": "Signup successful",
                "user_id": response.user.id
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)