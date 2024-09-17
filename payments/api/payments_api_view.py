from rest_framework import generics
from .models import PaymentsModel
from .payments_api_serializer import PaymentsSerializer

class PaymentsAPIView(generics.ListCreateAPIView):
    queryset = PaymentsModel.objects.all()
    serializer_class = PaymentsSerializer
