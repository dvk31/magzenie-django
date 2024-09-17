import logging
import traceback
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from django.conf import settings
from supabase import create_client, Client
from user.models import UsersModel

logger = logging.getLogger(__name__)

class CustomLoginView(APIView):
    @extend_schema(tags=["Authentication"])
    def post(self, request, *args, **kwargs):
        try:
            email = request.data.get('email')
            password = request.data.get('password')

            if not email or not password:
                return Response({"detail": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

            supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if auth_response.error:
                logger.error(f"Supabase authentication error: {auth_response.error.message}")
                return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

            access_token = auth_response.session.access_token
            refresh_token = auth_response.session.refresh_token

            try:
                user = UsersModel.objects.get(email=email)
                role = user.role
            except UsersModel.DoesNotExist:
                logger.error(f"User with email {email} exists in Supabase but not in Django database")
                return Response({"detail": "User account issue. Please contact support."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            response = Response({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "role": role
            }, status=status.HTTP_200_OK)

            response.set_cookie(
                key='refresh_token',
                value=refresh_token,
                httponly=True,
                secure=True,  # Set to True if using HTTPS
                samesite='Lax'
            )

            return response

        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            logger.error(traceback.format_exc())
            return Response({"detail": "An error occurred while processing your request."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


import logging
import traceback
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from django.conf import settings
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class CustomTokenRefreshView(APIView):
    @extend_schema(tags=["Authentication"])
    def post(self, request, *args, **kwargs):
        logger.info("Received request to refresh token")
        
        try:
            refresh_token = request.COOKIES.get('refresh_token')
            if not refresh_token:
                return Response({"detail": "Refresh token not found."}, status=status.HTTP_400_BAD_REQUEST)

            supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

            refresh_response = supabase.auth.refresh_session(refresh_token)

            if refresh_response.error:
                logger.error(f"Supabase token refresh error: {refresh_response.error.message}")
                return Response({"detail": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

            new_access_token = refresh_response.session.access_token
            new_refresh_token = refresh_response.session.refresh_token

            response = Response({
                "access_token": new_access_token,
                "refresh_token": new_refresh_token
            }, status=status.HTTP_200_OK)

            response.set_cookie(
                key='refresh_token',
                value=new_refresh_token,
                httponly=True,
                secure=True,  # Set to True if using HTTPS
                samesite='Lax'
            )

            return response

        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            logger.error(traceback.format_exc())
            return Response({"detail": "An error occurred while processing your request."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)