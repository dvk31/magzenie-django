from rest_framework import generics
from .models import AnalyticsModel
from .analytics_api_serializer import AnalyticsSerializer

class AnalyticsAPIView(generics.ListCreateAPIView):
    queryset = AnalyticsModel.objects.all()
    serializer_class = AnalyticsSerializer
