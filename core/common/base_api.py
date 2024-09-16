# core/common/base_api.py
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import gettext as _
from rest_framework.exceptions import APIException, ParseError, AuthenticationFailed, NotAuthenticated, PermissionDenied
from django.http import Http404
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import JsonResponse
from rest_framework.pagination import PageNumberPagination
from rest_framework import generics
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ApiResponseMixin:
    def api_response(self, data, status="success", message="Success", http_status=status.HTTP_200_OK):
        response = {
            "status": status,
            "message": message,
            "data": data
        }
        return Response(response, status=http_status)

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class BaseApiView(generics.GenericAPIView, ApiResponseMixin):
    pagination_class = CustomPagination

    def check_permissions(self, request):
        for permission in self.get_permissions():
            if not permission.has_permission(request, self):
                logger.debug(f"Permission check failed: {permission.__class__.__name__}")
                self.permission_denied(
                    request,
                    message=getattr(permission, 'message', None),
                    code=getattr(permission, 'code', None)
                )
    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response(serializer.data)
    def success_response(self, data=None, message=_("Success"), status_code=status.HTTP_200_OK):
        return Response({
            "status": "success",
            "message": message,
            "data": data,
        }, status=status_code)

    def error_response(self, message=_("An error occurred"), errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({
            "status": "error",
            "message": message,
            "errors": errors,
        }, status=status_code)

    def handle_exception(self, exc):
        logger.error(f'An exception occurred: {exc}', exc_info=True)
        if isinstance(exc, APIException):
            return self.error_response(message=str(exc.detail), status_code=exc.status_code)
        elif isinstance(exc, Http404):
            return self.error_response(message=_("The requested resource was not found."), status_code=status.HTTP_404_NOT_FOUND)
        elif isinstance(exc, DjangoPermissionDenied) or isinstance(exc, PermissionDenied):
            # Use a custom message if one is included in the exception, otherwise use a default message
            custom_message = getattr(exc, 'message', _("You do not have permission to perform this action."))
            help_link = getattr(exc, 'help', f"http://{self.request.get_host()}/docs/permissions")
            return self.error_response(message=custom_message, links={'help': help_link}, status_code=status.HTTP_403_FORBIDDEN)
        elif isinstance(exc, NotAuthenticated):
            return self.error_response(message=_("Authentication credentials were not provided."), status_code=status.HTTP_401_UNAUTHORIZED)
        elif isinstance(exc, AuthenticationFailed):
            return self.error_response(message=_("Invalid authentication credentials."), status_code=status.HTTP_401_UNAUTHORIZED)
        elif isinstance(exc, ParseError):
            return self.error_response(message=_("Malformed request."), status_code=status.HTTP_400_BAD_REQUEST)
        return self.error_response(message=_("A server error occurred."), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Override dispatch method for additional logging and pre/post processing

    def dispatch(self, request, *args, **kwargs):
        # Check if 'pre_process' is implemented in the current viewset instance
        if hasattr(self, 'pre_process'):
            self.pre_process(request)
        # Proceed with the normal dispatch process
        return super().dispatch(request, *args, **kwargs)


    def log_request(self, request):
        # Log the request method, path, and any other relevant information
        logger.info(f"Received {request.method} request for {request.get_full_path()}")
        # You can also log the body of the request, but be cautious with sensitive data
        if request.method in ['POST', 'PUT', 'PATCH']:
            logger.debug(f"Request data: {request.data}")

    # Additional methods as needed for your application

    def check_permissions(self, request):
        # Custom permission logic here
        return super().check_permissions(request)

    def paginate_queryset(self, queryset):
        # Custom pagination logic here
        return super().paginate_queryset(queryset)

    def filter_queryset(self, queryset):
        # Custom filtering logic here
        return super().filter_queryset(queryset)

    def perform_authentication(self, request):
        try:
            # Call the original perform_authentication method, which will use the authentication classes defined in your settings
            super().perform_authentication(request)
        except NotAuthenticated as exc:
            # If authentication fails, log this for auditing purposes
            logger.warning(f"Authentication failed for request {request.method} {request.get_full_path()}: {exc}")
            # You can then raise the exception to be handled by the handle_exception method
            # or handle it here directly if you want to customize the response
            raise NotAuthenticated(detail=str(exc))

    def log_request(self, request):
        # Custom logging logic here
        pass

  
    def finalize_response(self, request, response, *args, **kwargs):
        # Call the post_process method before the response is finalized
        response = self.post_process(response)
        # Now call the parent class's finalize_response method to complete the process
        return super().finalize_response(request, response, *args, **kwargs)

    def post_process(self, response):
        # Add a custom header to the response if it's a JsonResponse
        if isinstance(response, JsonResponse):
            response['X-Custom-Header'] = 'Custom Value'

        # Log the response data for auditing (be careful with sensitive data)
        # Make sure to log the data before creating the JsonResponse.
        # You can access the data from the response content if it's a JsonResponse.
        if isinstance(response, JsonResponse):
            logger.info(f"Response content: {response.content}")
        else:
            # If it's not a JsonResponse, it might be a DRF Response object which does have a `data` attribute.
            logger.info(f"Response data: {response.data}")

        # Perform any other response transformations or post-processing here

        # Return the modified response
        return response