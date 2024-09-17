from rest_framework import generics
from .models import MediaModel
from .media_api_serializer import MediaSerializer

class MediaAPIView(generics.ListCreateAPIView):
    queryset = MediaModel.objects.all()
    serializer_class = MediaSerializer
