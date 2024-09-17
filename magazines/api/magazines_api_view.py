from rest_framework import generics
from .models import MagazinesModel
from .magazines_api_serializer import MagazinesSerializer

class MagazinesAPIView(generics.ListCreateAPIView):
    queryset = MagazinesModel.objects.all()
    serializer_class = MagazinesSerializer
