from rest_framework import generics
from .models import Digital_setupModel
from .digital_setup_api_serializer import Digital_setupSerializer

class Digital_setupAPIView(generics.ListCreateAPIView):
    queryset = Digital_setupModel.objects.all()
    serializer_class = Digital_setupSerializer
