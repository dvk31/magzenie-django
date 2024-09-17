from rest_framework import generics
from .models import SupportModel
from .support_api_serializer import SupportSerializer

class SupportAPIView(generics.ListCreateAPIView):
    queryset = SupportModel.objects.all()
    serializer_class = SupportSerializer
