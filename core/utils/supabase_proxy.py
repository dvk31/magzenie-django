# core/api.py

from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
import requests
from django.conf import settings
from .supabase_config import SUPABASE_TABLES

class SupabaseViewSet(ViewSet):
    """
    A generic viewset for interacting with Supabase tables.
    """

    def list(self, request, table_name=None):
        if table_name is None:
            return Response({'error': 'Table name not provided'}, status=400)

        table_config = SUPABASE_TABLES.get(table_name)
        if not table_config:
            return Response({'error': 'Table not configured'}, status=404)

        url = f"{settings.SUPABASE_URL}/{table_name}?select={','.join(table_config['columns'])}"
        headers = {
            "apikey": settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.get(url, headers=headers)
        return Response(response.json())


    # core/api.py

# Add this method to your SupabaseViewSet class
def create(self, request, table_name=None):
    if table_name is None:
        return Response({'error': 'Table name not provided'}, status=400)

    table_config = SUPABASE_TABLES.get(table_name)
    if not table_config:
        return Response({'error': 'Table not configured'}, status=404)

    # Assuming the request.data contains the data to be inserted
    data = request.data
    url = f"{settings.SUPABASE_URL}/rest/v1/{table_name}"
    headers = {
        "apikey": settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"  # Adjust based on your preference
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        return Response(response.json(), status=status.HTTP_201_CREATED)
    else:
        return Response({'error': 'Failed to create record', 'details': response.json()}, status=response.status_code)