
from rest_framework import status
from rest_framework.response import Response
class ApiResponseMixin:
    
    def api_response(self, data, status="success", message="Success", http_status=status.HTTP_200_OK):
        response = {
            "status": status,
            "message": message,
            "data": data
        }
        return Response(response, status=http_status)