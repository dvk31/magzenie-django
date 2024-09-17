from rest_framework import generics
from .models import Print_ordersModel
from .print_orders_api_serializer import Print_ordersSerializer

class Print_ordersAPIView(generics.ListCreateAPIView):
    queryset = Print_ordersModel.objects.all()
    serializer_class = Print_ordersSerializer
