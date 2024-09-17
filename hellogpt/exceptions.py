# project/exceptions.py

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

from .serializers import ErrorResponseSerializer

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Log the exception
        logger.error(f"Exception: {exc}", exc_info=True)

        # Customize the response data
        error_response = {
            "success": False,
            "message": "",
        }

        if isinstance(response.data, dict):
            if 'detail' in response.data:
                error_response["message"] = response.data['detail']
            else:
                error_response["message"] = "An error occurred."
                error_response["errors"] = response.data
        else:
            error_response["message"] = "An error occurred."

        # Serialize the error response
        serializer = ErrorResponseSerializer(error_response)
        return Response(serializer.data, status=response.status_code)

    # For non-DRF exceptions, you might want to return a generic error response
    return Response(
        ErrorResponseSerializer({
            "success": False,
            "message": "An unexpected error occurred."
        }).data,
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
